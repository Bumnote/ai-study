import asyncio
import json
from datetime import datetime
import aiohttp
import mysql.connector 
from mysql.connector import Error 
from config import MYSQL_CONFIG
from dotenv import load_dotenv
import os

load_dotenv()

# Notion API 설정
NOTION_TOKEN = os.getenv("NOTION_API_KEY")  # 여기에 실제 API 키 입력
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

async def search_all_pages(session, query=""):
    """Notion API를 사용하여 모든 페이지 검색"""
    url = f"{BASE_URL}/search"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }
    
    all_results = []
    has_more = True
    start_cursor = None
    
    while has_more:
        payload = {
            "sort": {
                "direction": "descending",
                "timestamp": "last_edited_time"
            }
        }
        
        if query:
            payload["query"] = query
        
        if start_cursor:
            payload["start_cursor"] = start_cursor
        
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    all_results.extend(data.get("results", []))
                    has_more = data.get("has_more", False)
                    start_cursor = data.get("next_cursor")
                    
                    print(f"  📄 {len(all_results)}개 항목 수집 중...")
                elif response.status == 401:
                    print("❌ 인증 실패: API 키가 올바르지 않습니다.")
                    return []
                elif response.status == 403:
                    print("❌ 접근 거부: Integration에 적절한 권한이 없습니다.")
                    return []
                else:
                    error_text = await response.text()
                    print(f"❌ API 오류 ({response.status}): {error_text}")
                    return []
        except Exception as e:
            print(f"❌ 요청 중 오류 발생: {e}")
            return []
    
    return all_results

def extract_title(item):
    """페이지 또는 데이터베이스에서 제목 추출"""
    object_type = item.get('object')
    
    # 데이터베이스의 경우
    if object_type == 'database':
        title_array = item.get('title', [])
        if title_array:
            return title_array[0].get('plain_text', 'Untitled')
    
    # 페이지의 경우
    elif object_type == 'page':
        properties = item.get('properties', {})
        
        # title 타입 속성 찾기
        for key, value in properties.items():
            if isinstance(value, dict) and value.get('type') == 'title':
                title_array = value.get('title', [])
                if title_array:
                    return title_array[0].get('plain_text', 'Untitled')
    
    return 'Untitled'

def extract_icon(icon_obj):
    """아이콘 정보 추출"""
    if not isinstance(icon_obj, dict):
        return None
    
    icon_type = icon_obj.get('type')
    if icon_type == 'emoji':
        return icon_obj.get('emoji')
    elif icon_type == 'external':
        return icon_obj.get('external', {}).get('url')
    elif icon_type == 'file':
        return icon_obj.get('file', {}).get('url')
    return None

def extract_cover(cover_obj):
    """커버 이미지 정보 추출"""
    if not isinstance(cover_obj, dict):
        return None
    
    cover_type = cover_obj.get('type')
    if cover_type == 'external':
        return cover_obj.get('external', {}).get('url')
    elif cover_type == 'file':
        return cover_obj.get('file', {}).get('url')
    return None

def extract_parent_info(parent_obj):
    """부모 정보 추출"""
    if not isinstance(parent_obj, dict):
        return None, None
    
    parent_type = parent_obj.get('type')
    parent_id = parent_obj.get(parent_type) if parent_type else None
    return parent_type, parent_id

def parse_page_data(item):
    """페이지 데이터를 파싱하여 필요한 정보만 추출"""
    parent_type, parent_id = extract_parent_info(item.get('parent'))
    
    return {
        'id': item.get('id'),
        'object': item.get('object'),
        'title': extract_title(item),
        'created_time': item.get('created_time'),
        'last_edited_time': item.get('last_edited_time'),
        'created_by': item.get('created_by', {}).get('id'),
        'last_edited_by': item.get('last_edited_by', {}).get('id'),
        'url': item.get('url'),
        'public_url': item.get('public_url'),
        'archived': item.get('archived', False),
        'in_trash': item.get('in_trash', False),
        'parent_type': parent_type,
        'parent_id': parent_id,
        'icon': extract_icon(item.get('icon')),
        'cover': extract_cover(item.get('cover')),
    }

def format_datetime(dt_string):
    """ISO 형식 날짜를 읽기 쉬운 형식으로 변환"""
    if dt_string:
        try:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return dt_string
    return 'N/A'

def save_to_json(pages, filename='notion_pages.json'):
    """페이지 데이터를 JSON 파일로 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"💾 데이터가 {filename}에 저장되었습니다.")

def save_to_html(pages, filename='notion_pages.html'):
    """페이지 데이터를 HTML 테이블로 저장"""
    
    # 통계 계산
    total_pages = len(pages)
    active_pages = sum(1 for p in pages if not p.get('archived', False))
    archived_pages = sum(1 for p in pages if p.get('archived', False))
    databases = sum(1 for p in pages if p.get('object') == 'database')
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notion Pages Metadata</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px 40px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-number {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: #6c757d;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .table-container {{
            padding: 30px 40px;
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        thead {{
            background-color: #495057;
            color: white;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        th {{
            padding: 16px 12px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }}
        
        tbody tr {{
            border-bottom: 1px solid #e9ecef;
            transition: background-color 0.2s;
        }}
        
        tbody tr:hover {{
            background-color: #f8f9fa;
        }}
        
        td {{
            padding: 14px 12px;
            font-size: 0.95rem;
        }}
        
        .icon-cell {{
            font-size: 1.5rem;
            text-align: center;
        }}
        
        .title-cell {{
            font-weight: 600;
            color: #212529;
        }}
        
        .archived {{
            opacity: 0.6;
        }}
        
        a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s;
        }}
        
        a:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        
        .badge-active {{
            background-color: #d4edda;
            color: #155724;
        }}
        
        .badge-archived {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        
        .badge-database {{
            background-color: #d1ecf1;
            color: #0c5460;
        }}
        
        .badge-page {{
            background-color: #fff3cd;
            color: #856404;
        }}
        
        .date-cell {{
            color: #6c757d;
            font-size: 0.9rem;
        }}
        
        .footer {{
            padding: 20px 40px;
            text-align: center;
            background-color: #f8f9fa;
            color: #6c757d;
            font-size: 0.9rem;
            border-top: 1px solid #dee2e6;
        }}
        
        .search-box {{
            padding: 20px 40px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .search-input {{
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 10px;
            margin-top: 10px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border: 2px solid #dee2e6;
            background: white;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover {{
            border-color: #667eea;
        }}
        
        .filter-btn.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Notion Workspace</h1>
            <div class="subtitle">페이지 메타데이터 리포트</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_pages}</div>
                <div class="stat-label">전체</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_pages}</div>
                <div class="stat-label">활성</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{archived_pages}</div>
                <div class="stat-label">보관됨</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{databases}</div>
                <div class="stat-label">데이터베이스</div>
            </div>
        </div>
        
        <div class="search-box">
            <input 
                type="text" 
                class="search-input" 
                id="searchInput"
                placeholder="🔍 제목으로 검색..." 
                onkeyup="filterTable()"
            >
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterByType('all')">전체</button>
                <button class="filter-btn" onclick="filterByType('page')">페이지만</button>
                <button class="filter-btn" onclick="filterByType('database')">데이터베이스만</button>
                <button class="filter-btn" onclick="filterByType('active')">활성만</button>
                <button class="filter-btn" onclick="filterByType('archived')">보관됨만</button>
            </div>
        </div>
        
        <div class="table-container">
            <table id="pageTable">
                <thead>
                    <tr>
                        <th style="width: 50px;">아이콘</th>
                        <th>제목</th>
                        <th style="width: 100px;">타입</th>
                        <th style="width: 180px;">생성 날짜</th>
                        <th style="width: 180px;">마지막 수정</th>
                        <th style="width: 100px;">상태</th>
                        <th style="width: 100px;">링크</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for page in pages:
        icon = page.get('icon')
        # 아이콘이 URL이면 이모지로 변환, None이면 기본 이모지 사용
        if icon:
            if icon.startswith('http'):
                icon = '🔗'  # URL 아이콘은 링크 이모지로 표시
        else:
            icon = '📄'  # 아이콘이 없으면 기본 이모지
        
        title = page.get('title', 'Untitled')
        object_type = page.get('object', 'page')
        created = format_datetime(page.get('created_time'))
        edited = format_datetime(page.get('last_edited_time'))
        archived = page.get('archived', False)
        url = page.get('url', '#')
        
        type_badge = f'<span class="badge badge-database">데이터베이스</span>' if object_type == 'database' else '<span class="badge badge-page">페이지</span>'
        status_badge = '<span class="badge badge-archived">보관됨</span>' if archived else '<span class="badge badge-active">활성</span>'
        row_class = 'archived' if archived else ''
        
        html_content += f"""
                    <tr class="{row_class}" data-type="{object_type}" data-archived="{str(archived).lower()}">
                        <td class="icon-cell">{icon}</td>
                        <td class="title-cell">{title}</td>
                        <td>{type_badge}</td>
                        <td class="date-cell">{created}</td>
                        <td class="date-cell">{edited}</td>
                        <td>{status_badge}</td>
                        <td><a href="{url}" target="_blank">열기 →</a></td>
                    </tr>
"""
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            Generated with Notion API | Python Script
        </div>
    </div>
    
    <script>
        let currentFilter = 'all';
        
        function filterTable() {
            const searchInput = document.getElementById('searchInput');
            const query = searchInput.value.toLowerCase();
            const table = document.getElementById('pageTable');
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            
            for (let row of rows) {
                const title = row.cells[1].textContent.toLowerCase();
                const type = row.getAttribute('data-type');
                const archived = row.getAttribute('data-archived') === 'true';
                
                let showByFilter = false;
                if (currentFilter === 'all') {
                    showByFilter = true;
                } else if (currentFilter === 'page') {
                    showByFilter = type === 'page';
                } else if (currentFilter === 'database') {
                    showByFilter = type === 'database';
                } else if (currentFilter === 'active') {
                    showByFilter = !archived;
                } else if (currentFilter === 'archived') {
                    showByFilter = archived;
                }
                
                const showBySearch = title.includes(query);
                
                if (showByFilter && showBySearch) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            }
        }
        
        function filterByType(type) {
            currentFilter = type;
            
            // 버튼 활성화 상태 변경
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            filterTable();
        }
    </script>
</body>
</html>
"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"🎨 HTML 리포트가 {filename}에 저장되었습니다.")


def save_to_database(pages, db_config=None):
    """페이지 데이터를 MySQL 데이터베이스에 저장"""
    
    # 기본 설정 (환경에 맞게 수정)
    if db_config is None:
        db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': 'your_password',  # 실제 비밀번호로 변경
            'database': 'notion_db'
        }
    
    try:
        # MySQL 연결
        print("🔌 MySQL 데이터베이스 연결 중...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 데이터베이스 생성 (없을 경우)
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {db_config['database']}")
        
        # 테이블 생성
        create_table_query = """
        CREATE TABLE IF NOT EXISTS notion_pages (
            id VARCHAR(36) PRIMARY KEY,
            object_type VARCHAR(20) NOT NULL,
            title VARCHAR(500) NOT NULL,
            created_time DATETIME NOT NULL,
            last_edited_time DATETIME NOT NULL,
            created_by VARCHAR(36),
            last_edited_by VARCHAR(36),
            url TEXT,
            public_url TEXT,
            archived BOOLEAN DEFAULT FALSE,
            in_trash BOOLEAN DEFAULT FALSE,
            parent_type VARCHAR(50),
            parent_id VARCHAR(36),
            icon TEXT,
            cover TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_title (title(100)),
            INDEX idx_object_type (object_type),
            INDEX idx_archived (archived),
            INDEX idx_created_time (created_time DESC),
            INDEX idx_last_edited_time (last_edited_time DESC),
            INDEX idx_parent_id (parent_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        cursor.execute(create_table_query)
        print("✅ 테이블 생성 완료")
        
        # 데이터 삽입/업데이트 (UPSERT)
        insert_query = """
        INSERT INTO notion_pages (
            id, object_type, title, created_time, last_edited_time,
            created_by, last_edited_by, url, public_url,
            archived, in_trash, parent_type, parent_id, icon, cover
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            object_type = VALUES(object_type),
            title = VALUES(title),
            last_edited_time = VALUES(last_edited_time),
            last_edited_by = VALUES(last_edited_by),
            url = VALUES(url),
            public_url = VALUES(public_url),
            archived = VALUES(archived),
            in_trash = VALUES(in_trash),
            parent_type = VALUES(parent_type),
            parent_id = VALUES(parent_id),
            icon = VALUES(icon),
            cover = VALUES(cover),
            updated_at = CURRENT_TIMESTAMP
        """
        
        insert_count = 0
        update_count = 0
        
        for page in pages:
            # ISO 8601 날짜를 MySQL DATETIME 형식으로 변환
            created_time = page.get('created_time', '').replace('Z', '').replace('T', ' ')[:19]
            last_edited_time = page.get('last_edited_time', '').replace('Z', '').replace('T', ' ')[:19]
            
            values = (
                page.get('id'),
                page.get('object'),
                page.get('title'),
                created_time,
                last_edited_time,
                page.get('created_by'),
                page.get('last_edited_by'),
                page.get('url'),
                page.get('public_url'),
                page.get('archived', False),
                page.get('in_trash', False),
                page.get('parent_type'),
                page.get('parent_id'),
                page.get('icon'),
                page.get('cover')
            )
            
            cursor.execute(insert_query, values)
            
            if cursor.rowcount == 1:
                insert_count += 1
            elif cursor.rowcount == 2:
                update_count += 1
        
        # 커밋
        conn.commit()
        
        print(f"💾 MySQL 저장 완료:")
        print(f"   • 새로 추가: {insert_count}개")
        print(f"   • 업데이트: {update_count}개")
        print(f"   • 전체: {len(pages)}개")
        
        # 통계 출력
        cursor.execute("SELECT COUNT(*) FROM notion_pages")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM notion_pages WHERE archived = FALSE")
        active = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM notion_pages WHERE object_type = 'database'")
        databases = cursor.fetchone()[0]
        
        print(f"\n📊 데이터베이스 통계:")
        print(f"   • 전체 항목: {total}개")
        print(f"   • 활성 항목: {active}개")
        print(f"   • 데이터베이스: {databases}개")
        
    except Error as e:
        print(f"❌ MySQL 오류: {e}")
        if conn:
            conn.rollback()
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("🔌 MySQL 연결 종료")


# 또는 환경변수를 사용하는 방법
def save_to_database_with_env(pages):
    """환경변수를 사용한 MySQL 연결"""
    import os
    
    db_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE', 'notion_db')
    }
    
    save_to_database(pages, db_config)


# 쿼리 헬퍼 함수들
def query_active_pages(db_config):
    """활성 페이지 조회"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, title, created_time, last_edited_time, url
            FROM notion_pages
            WHERE archived = FALSE
            ORDER BY last_edited_time DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        return results
        
    except Error as e:
        print(f"❌ 쿼리 오류: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def search_pages_by_title(db_config, search_term):
    """제목으로 페이지 검색"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, title, object_type, created_time, url
            FROM notion_pages
            WHERE title LIKE %s
            ORDER BY last_edited_time DESC
        """, (f'%{search_term}%',))
        
        results = cursor.fetchall()
        return results
        
    except Error as e:
        print(f"❌ 검색 오류: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    


def print_summary(pages):
    """콘솔에 요약 정보 출력"""
    print("\n" + "="*90)
    print(f"{'아이콘':<6} {'제목':<35} {'생성일':<20} {'수정일':<20}")
    print("="*90)
    
    for page in pages[:15]:
        icon = page.get('icon')
        # 아이콘이 URL이면 🔗 사용, None이면 📄 사용
        if icon:
            if icon.startswith('http'):
                icon = '🔗'
        else:
            icon = '📄'
        
        title = page.get('title', 'Untitled')[:33]
        created = format_datetime(page.get('created_time'))[:19]
        edited = format_datetime(page.get('last_edited_time'))[:19]
        
        print(f"{icon:<6} {title:<35} {created:<20} {edited:<20}")
    
    if len(pages) > 15:
        print(f"\n... 그 외 {len(pages) - 15}개 항목")
    
    print("="*90)

async def main():
    """메인 실행 함수"""
    print("="*70)
    print("🚀 Notion 워크스페이스 메타데이터 수집 도구 (Direct API)")
    print("="*70)
    print()
    
    if NOTION_TOKEN == "your_notion_api_key_here":
        print("❌ NOTION_TOKEN이 설정되지 않았습니다.")
        print("스크립트 상단의 NOTION_TOKEN 변수를 실제 API 키로 변경해주세요.")
        print()
        print("Notion API 키 발급 방법:")
        print("  1. https://www.notion.so/my-integrations 방문")
        print("  2. 'New integration' 클릭")
        print("  3. Integration 이름 입력 및 생성")
        print("  4. 'Internal Integration Token' 복사")
        print("  5. Notion 페이지에서 '...' → 'Add connections' → Integration 선택")
        return
    
    print("🔐 Notion API에 연결 중...\n")
    
    async with aiohttp.ClientSession() as session:
        # 모든 페이지 검색
        raw_results = await search_all_pages(session)
        
        if raw_results:
            # 데이터 파싱
            pages = [parse_page_data(item) for item in raw_results]
            
            # 생성일 기준 정렬 (최신순)
            pages.sort(key=lambda x: x.get('created_time', ''), reverse=True)
            
            print(f"\n✅ 총 {len(pages)}개 항목 수집 완료!\n")
            
            # 결과 출력
            print_summary(pages)
            
            # 파일로 저장
            print("\n📁 파일 저장 중...")
            save_to_json(pages)
            save_to_html(pages)
            save_to_database(pages)
            
            print("\n" + "="*70)
            print("✅ 모든 작업이 완료되었습니다!")
            print("="*70)
            print(f"\n📊 생성된 파일:")
            print(f"  • notion_pages.json - JSON 형식 데이터")
            print(f"  • notion_pages.html - 시각화된 HTML 리포트")
            print(f"\n💡 HTML 파일을 브라우저에서 열어 검색/필터링 기능을 사용할 수 있습니다.")
        else:
            print("\n" + "="*70)
            print("⚠️ 가져온 항목이 없습니다.")
            print("="*70)
            print("\n다음을 확인해주세요:")
            print("  1. NOTION_TOKEN이 올바른지 확인 (secret_로 시작)")
            print("  2. Notion Integration이 생성되었는지 확인")
            print("  3. 페이지/데이터베이스에 Integration 접근 권한 부여")
            print("     (페이지 우측 상단 ... → Add connections)")
            print("  4. 인터넷 연결 확인")

if __name__ == "__main__":
    print("✅ aiohttp 패키지 확인 중...\n")
    try:
        import aiohttp
    except ImportError:
        print("❌ aiohttp 패키지가 설치되어 있지 않습니다.")
        print("다음 명령어로 설치해주세요:")
        print("  pip install aiohttp\n")
        exit(1)
    
    # 비동기 실행
    asyncio.run(main())