# [Tazamore] 타이핑 문장 조회 성능 개선기(9.33초 → 0.002초)

> **📍 Local & DB Spec
Local** : Mac OS M3 Pro
**DB** : Docker MySQL 8.0
> 

## 1. 들어가며

 취준생들을 위한 힐링 타이핑 프로젝트인 “Tazamore” 프로젝트 기능에는 문장을 랜덤으로  20개 가져오는 기능이 있다. 개발을 하는 과정에서 덤프 데이터의 개수가 100개 미만 이었기 때문에 해당 기능에 대해서 문제점을 크게 느끼지 못했다. 개발을 다 끝내고 나서 문득 이런 생각이 들었다.

<aside>

📍문장의 개수가 만약 100개가 아닌 100만, 1000만 개라면 어떻게 될까? 

</aside>

 현재 코드 로직은 전체에서 랜덤으로 20개를 가져오는 것이기 때문에 만약 1,000만 개의 문장 데이터가 존재한다면 정말 많은 시간이 걸릴 것으로 추측된다. 내가 사용자이더라도 타이핑을 하기 위해 문장을 불러오는 화면에서 매번 5초 ~ 10초 이상이 걸린다면 바로 웹 사이트를 나갈 것 같다.  이런 일은 있어선 안되기 때문에 문장 조회 기능을 개선해보도록 하자! 

## 2. 문제점 파악 ❗️

### 2.1 코드 파악

현재 문장 조회 기능은 다음과 같이 구현되어있다.

```java
  @Override
  public List<Phrase> getRandomPhrases(int phraseCount) {

    NumberExpression<Double> rand = numberTemplate(Double.class, "rand");

    return queryFactory
        .selectFrom(phrase)
        .orderBy(rand.asc())
        .limit(phraseCount)
        .fetch();
  }
```

`QueryDsl` 을 활용하여 코드를 구현했고, mysql rand() 함수를 인식할 수 있도록 하여 랜덤으로 불러온 데이터들 속에서 주어진 phraseCount 개수만큼 문장을 List<Phrase> 형태로 반환하는 메서드이다. 

### 2.2 원인 분석

이 메서드에는 어떤 문제가 있을까? 그것은 바로 `rand.asc()` 코드에 있다. mysql에서 rand() 함수를 실행하게 되면 전체 테이블의 행을 모두 읽게 된다. 즉, `Full Scan` 해야 한다는 문제가 있다. 또한, 랜덤 정렬하여 문장을 상위 phraseCount 개수만큼 불러오기 때문에  Primary Key에 대한 인덱스 효과도 얻을 수 없다. 문제점을 정리해보면 다음과 같다.

1. 테이블의 모든 행을 읽는 Full Scan 현상 발생
2. 랜덤 정렬로 인한 인덱스 효과 X
3. 매번 전체 데이터셋 처리로 인한 메모리 부하

이 3가지 문제들을 한번 해결해보록 하자.

## 3. 문제 해결 준비 ‼️

### 3.1 데이터 셋 전처리 (1,000만 데이터)

 데이터 셋이 적으면 개선 결과를 쉽게 파악하기 힘들기 때문에 1,000만 개의 문장(Phrase) 데이터를 넣어보도록 하자. 별도의 컨트롤러를 만들어서 1,000만 개의 데이터를 삽입하였다.  

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image.png)

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%201.png)

 아래 사진은 1,000만 개의 데이터를 넣을 때, Grafana를 활용하여 모니터링한 결과이다. 가용 가능한 Thread 10개를 전부 사용하면서 데이터를 넣는 것을 실시간으로 확인할 수 있었다.

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%202.png)

 이처럼 멀티 스레드 환경에서 데이터를 넣었음에도 불구하고, 약 27분의 시간이 걸렸다. 삽입 시간을 통해서도 1,000만 개의 데이터가 얼마나 많은 수치인지 깨달았다. 이제 1,000만 개의 데이터에 대해서 기존에 작성되어있던 쿼리문을 수행시켜보자. 어떤 결과가 나올까?

### 3.2 기존 코드 실행 결과

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%203.png)

1,000만 데이터를 기준으로 기존 문장 조회 쿼리문을 실행한 결과 `9.33초`라는 시간이 걸렸다. 사용자가 문장을 매번 불러올 때마다 9~10초를 기다려주지 않을 것 같다. 

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%204.png)

`explain` 실행문으로 해당 쿼리문을 분석해보자. 여기서 살펴보아야 할 점은 Extra 영역의 `Using temporary` 와 `Using filesort` 이다.

- Using temporary
    - 정렬 작업을 위해 임시 테이블이 필요한 경우 Using temporary 라는 키워드가 등장한다. 즉, 인덱스를 통해서 정렬을 수행할 수 없거나, filesort 만으로 정렬을 완료할 수 없는 경우 임시 테이블을 생성하여 데이터들을 모두 담아 정렬하는 작업이다.
- Using filesort
    - 인덱스를 통해서 정렬(order by)할 수 없을 때, filesort를 사용한다. rand() 함수로 생성된 무작위 값을 기준으로 임시 테이블의 모든 행을 정렬한다는 것이다.

 위 2가지 과정은 모두 메모리와 CPU에 큰 오버헤드를 발생시킨다. 따라서, 최대한 발생하지 않도록 쿼리 튜닝 등의 작업을 하는 것이 좋다고 한다. 

## 4. 문제 해결 과정 💁🏻‍♂️

이제 오랜 시간 걸리는 문장 조회 기능을 개선해보자. 개선 방법에 대해서 생각난 방법은 다음과 같다.

1. Clustered(PK) Index 활용
2. Index 활용을 위한 코드 개선

위 내용들을 한번씩 적용해보고, 얼마나 개선이 가능한 지 검증해보자. 

### 4.1 Clustered(PK) Index 활용

`Clustered(PK) Index` 란, MySQL InnoDB에서 PK를 생성하면 자동으로 Clustered Index를 생성해준다. 이 Clustered Index는 실제 데이터의 위치를 가지고 있는 인덱스이다. 그렇기에 테이블 당 하나만 존재하고, Clustered Index에 해당하는 컬럼을 기준으로 데이터를 정렬하기 때문에 조회 속도가 빨라질 수 있다. 

이러한 개념을 토대로 나는 쿼리를 다음과 같이 수정해보았다.

```sql
select * 
from phrase as p1 
	inner join (select id from phrase order by rand() limit 20) as p2
	on p1.id = p2.id;
```

 내부 쿼리에서 Clustered Index에 해당하는 id 컬럼만을 조회함으로써 성능을 높였다. 이렇게 index에 해당하는 컬럼만을 조회하는 것은 `Covering Index` 라고도 한다. 이렇게 작성한 쿼리를 실제 1,000만 데이터로 조회해보고, explaing 쿼리 실행 계획문을 살펴보자.

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%205.png)

  `9.33초 → 3.60초`로 약 `61.4%` 정도 개선된 것을 확인할 수 있었다. explain 쿼리 실행 계획문을 보더라도 서브 쿼리 실행문에서 `Using index` 활용한 것을 확인할 수 있었고, type 영역의 `index`, key 영역에서도 `PRIMARY` 를 사용했다는 것을 확인할 수 있다. 

 또한, inner join 문에서도 20개의 rows들에 대해서 인덱스로 빠르게(eq_ref) 가져왔기 때문에, 마무리 단계에서 전체 테이블을 스캔하는 비효율을 피할 수 있었다. 

 하지만, 여전히 `order by rand()` 정렬 기준으로 인하여 여전히 모든 행을 정렬해야 하므로 Using temporary, Using filesort가 표시된 것을 확인할 수 있었다. 이 부분만 더 개선한다면 보다 더 파격적인 성능 개선이 가능할 것이다. 

### 4.2 CTE 방식 활용

 어떻게 하면 인덱스를 최대로 활용하여 더 파격적인 성능 개선을 할 수 있을까? 위 방법에서 우리는 서브 쿼리에 Clustered Index를 활용하여 조금이나마 인덱스를 활용한 성능 개선을 도출해냈지만, order by rand() 함수의 비효율적인 로직은 해결하지 못했다. order by rand() 함수는 절대로 인덱스를 활용할 수 없기 때문에 이 로직을 제거한다면 성능을 더욱 개선할 수 있지 않을까?

 CTE(Common Table Expression) 방식을 활용해볼 수 있을 것 같다. `CTE` 란, SQL에서 사용되는 기능으로 복잡한 쿼리를 간결하게 작성할 수 있게 해주는 임시 결과 집합입니다. 즉, 복잡한 서브 쿼리를 WITH 절로 따로 분리하여 여러 번 재사용할 수 있게 해주는 도구라고 할 수 있다. 이 CTE 로직을 다음과 같이 적용해보자.

<aside>

> 로직: id 값 중 최솟값, 최댓값 계산 → 사이에 존재하는 랜덤 Id 생성 → 기존 테이블과 Join
> 

```sql
WITH max_min_id AS (
    SELECT MIN(id) AS min_id, MAX(id) AS max_id
    FROM phrase
),
random_ids AS (
    SELECT FLOOR(RAND() * (m.max_id - m.min_id + 1)) + m.min_id AS random_id
    FROM max_min_id AS m
    JOIN phrase AS p
    LIMIT 20
)
SELECT p.*
FROM phrase AS p
INNER JOIN random_ids AS r ON p.id = r.random_id;
```

</aside>

이 쿼리를 실제 1,000만 데이터를 토대로 실행해보면 다음과 같은 결과를 얻을 수 있다.

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%206.png)

 실행 시간이 정말 눈에 띄게 단축된 것을 확인할 수 있다. `3.60초 → 0.02초` 로 약 99.44% 개선된 것을 확인할 수 있다. 실행 계획을 분석해보면 다음과 같다. (실행 계획은 id 값이 높은 순서대로, 같다면 위에서 아래로 읽는다.)

1. id = 3 →  max_min_id 서브 쿼리 
    - `select_type = DERIVED` 라는 것은 임시 테이블을 생성했다는 것을 뜻한다.
    - `Extra = Select tables` 라는 것은 MySQL에서 테이블을 읽지도 않고, 해당 값들을 인덱스에서 바로 가져온다는 의미이다. 즉, 속도가 매우 빠르다는 것을 의미합니다.
2. id = 2 → random_idx 서브 쿼리
    - `select_type = DERIVED` 마찬가지로 임시 테이블을 생성했다는 것을 의미한다.
    - `type = index` 인덱스를 활용하긴 했지만, `rows = 9940783` 값을 통해 선택적 조회가 아닌 전체 스캔을 했다는 것을 알 수 있다.
3. id = 3 → PRIMARY 쿼리 (최종 조인)
    - `select_type = PRIMARY` 메인 쿼리임을 뜻한다.
    - `table = derived2` 랜덤 ID 임시 테이블로 생성된 20개 행을 모두(type = ALL) 읽습니다.
    - `type = eq_ref` 기본 키 인덱스를 통해서 각 ID에 해당하는 행을 직접 찾아오기 때문에 효율적인 조인 방식이라고 할 수 있다.

 쿼리 실행 계획을 종합해보면 CTE 방식을 활용한 쿼리는 존재하는 id 값 중 최솟값, 최댓값 id 값을 빠르게 가져오지만, **무작위 ID를 생성하는 과정에서 여전히 전체 인덱스 스캔을 실행**하는 것을 확인할 수 있었다. 즉, Join 연산을 통해 rand() 함수를 실행시키려는 시도가 LIMIT 절이 적용되기 전에 모든 인덱스 행을 읽게 만드는 것이다.

 이는 기존의 `order by rand()` 방식과 동일하게 대용량 데이터에서 성능 문제를 일으킬 수 있다. 또한, 곰곰히 생각해보면 위 방식은 데이터가 일부가 소실되어 불연속적인 id 값을 가질 때, phraseCount 개수만큼 데이터를 가지고 오지 못할 수도 있는 문제점이 있다. 따라서 이 쿼리는 겉보기와 달리 **효율적인 최적화 방안이 아니다**. 그러면 어떻게 더욱 최적화를 할 수 있을까? 

### 4.3 새로운 컬럼 추가 방식

 기존 식별 id 값이 아닌 아예 랜덤한 id 값을 테이블 컬럼으로 추가하는 방법이 있을 것 같다. 즉, 테이블 컬럼을 추가하여 단일 인덱스를 추가하여 전체 조회(Full Scan)가 아닌, 구간 조회를 할 수 있도록 하는 것이다. 기존 CTE 방식보다 불연속적인 Id 값과는 무관하게 정확한 phraseCount 개수만큼 데이터를 조회할 수 있고, 데이터가 증가하더라도 성능을 유지할 수 있다는 점이 보다 개선된 내용이라고 할 수 있다. 그러면 컬럼을 추가하고 검증을 해보자.

1. **Phrase 테이블 rand_id 컬럼 추가**
    
    ```sql
    ALTER TABLE phrase ADD COLUMN rand_id INT;
    ```
    
2. **Procedure 활용한 rand_id 데이터 추가 및 인덱스 추가**
    
    ```sql
    DELIMITER $$
    CREATE PROCEDURE UpdateNullRandIdOnly()
    BEGIN
        DECLARE null_count INT;
        DECLARE batch_size INT DEFAULT 500000;
        DECLARE current_batch INT DEFAULT 0;
        DECLARE total_batches INT;
        
        SELECT COUNT(*) - COUNT(rand_id) INTO null_count FROM phrase;
        
        IF null_count > 0 THEN
            SET total_batches = CEIL(null_count / batch_size);
            
            WHILE current_batch < total_batches DO
                UPDATE phrase 
                SET rand_id = FLOOR(RAND() * 100000000)
                WHERE rand_id IS NULL
                LIMIT 500000;
                
                SET current_batch = current_batch + 1;
            END WHILE;
        END IF;
        
        SET @index_exists = 0;
        SELECT COUNT(*) INTO @index_exists
        FROM information_schema.STATISTICS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'phrase' 
        AND INDEX_NAME = 'idx_phrase_rand_id';
        
        IF @index_exists = 0 THEN
            CREATE INDEX idx_phrase_rand_id ON phrase(rand_id);
        END IF;
        
    END$$
    DELIMITER ;
    
    CALL UpdateNullRandIdOnly();
    ```
    
    ![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%207.png)
    
    약 4분 30초 가량의 시간을 통해서 rand_id 데이터 1,000만 건 추가 완료!  
    
3. **쿼리문 실행 결과**
    
    ![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%208.png)
    
     오잉? rand_id 컬럼을 새롭게 생성하고, rand_id 컬럼에 대한 인덱스까지 만들었는데, 오히려 `0.81초` 라는 수치가 결과로 나왔다. 또한, Extra 영역에 `Using where` 라는 문장만 있고, 기대했던 `Using index` 라는 문장은 없다는 것을 확인했고, `type = index` 를 보아 `Full Scan` 작업이 이루어진 것을 확인할 수 있다. 
    
4. **쿼리문 수정**
    
     인덱스를 활용하지 않은 이유는 무엇일까? 그것은 바로 where 절에 있는 rand() 함수 때문이다. rand() 함수가 정말 유용하지만, 문제가 많은 것 같다. rand() 함수가 한번 실행이 되고, 값이 고정이 되지만, 옵티마이저가 해당 rand() 값이 어떤 값을 반환해줄 지 모르기 때문에 일단 index scan 작업을 실행하여 해당 where 절을 만족하는 row 데이터를 20개 찾는 것이다.  우리가 인덱스를 활용하는 이유는 범위 조회 성능을 높이기 위해서인데, 현재 쿼리문에서는 이 장점을 극대화하지 못하고 있다. 
    
     그러면 rand() 함수를 사용하지 않고, 상수를 통해서 조회하면 어떻게 될까? 정말 빨라질까? 쿼리가 동작하는 시간이 단계별로 얼마나 걸렸는지 확인할 수 있는 `쿼리 프로파일링` 기능을 통해서 rand() 함수를 활용한 조회와 상수를 활용한 조회를 비교해보자.
    
    ![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%209.png)
    
     놀라운 결과가 나왔다. 무려 `0.002초`까지 단축이 되었다. 여기서 주어지는 상수는 애플리케이션 단에서 정해주면 되기 때문에 해당 방식을 활용하기로 결정했다. 그럼 어떤 차이로 인해서 해당 0.002초라는 수치가 나온 것일까? 바로 explain 명령어를 통해서 해당 쿼리의 실행 계획을 확인해보았다.
    
    ![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%2010.png)
    
     가장 먼저 눈에 띄는 것은 `Using index condition` 이다. 이는 `Index Condition Pushdown(ICP)`으로 인한 표시이며, 이 경우 MySQL Where 조건을 스토리지 엔진에 전달하여 스토리지 엔진에서 필터링된 데이터만 MySQL 엔진에 전달하는 효과적인 처리 방법이다. 더불어 이전에 생성한 rand_id 컬럼을 활용한 인덱스를 통해서 `Index Range Scan`이 동작하는 것을 확인할 수 있다. 이러한 내용들이 적용되어 `0.002초`까지 성능을 개선할 수 있었다. 
    

## 5. 결과

 지금까지의 작업 및 검증을 통해서 `9.33초 → 0.002초` 로 문장 조회 성능을 개선해보았다. 이제 이를 바탕으로 애플리케이션 단에서 반영시키고, 포스트맨에서 테스트 해보자. 결과는 다음과 같았다.

### 5.1 개선 전

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%2011.png)

### 5.2 개선 후

![image.png](%5BTazamore%5D%20%ED%83%80%EC%9D%B4%ED%95%91%20%EB%AC%B8%EC%9E%A5%20%EC%A1%B0%ED%9A%8C%20%EC%84%B1%EB%8A%A5%20%EA%B0%9C%EC%84%A0%EA%B8%B0(9%2033%EC%B4%88%20%E2%86%92%200%20002%EC%B4%88)%2025f10f5b107a80bca6d0e799bd2729ed/image%2012.png)

## 6. 깨달은 점 🙋🏻‍♂️

### 6.1 작은 데이터에서는 보이지 않는 문제들

 100개 정도의 덤프 데이터로는 성능 문제를 전혀 느낄 수 없었습니다. 요즘같은 빅데이터 시대에서 데이터 양을 고려하지 않고, 단순히 동작하게만 하는 코드를 짜는 건 어리석은 행동이라는 것을 새롭게 배웠습니다.

### 6.2 함수 사용의 숨겨진 비용

겉보기에는 단순해 보이고, 원하는 동작을 수행시켜주는 `ORDER BY RAND()` 함수. 실제로는 **옵티마이저가 최적화할 수 없는 블랙박스** 함수라고 생각합니다. 즉, 함수의 내부 동작을 고려하지 않고, 비효율적인 코드를 작성했던 과거의 모습을 통해서 DB 쿼리문도 제대로 알고 사용해야 한다는 점을 배웠습니다.

**MySQL 옵티마이저의 한계**

```sql
-- 옵티마이저가 보는 것
WHERE rand_id >= FLOOR(RAND() * 100000000)
-- "이 값이 언제 어떻게 바뀔지 모르겠어... 그냥 전체 스캔하자"

-- 개선된 방식
WHERE rand_id >= 50000000
-- "아! 50000000부터 시작하면 되겠네!"
```

### 6.3 인덱스 설계의 중요성

**단순한 인덱스 추가가 답이 아니라는 것**을 깨달았습니다. 실제로 이번 성능 개선 과정 중에서 `rand_id` 컬럼 추가 및 인덱스를 생성했음에도 불구하고, 오히려 성능이 더 나빠지는 현상을 경험했습니다. **인덱스는 쿼리 패턴과 함께 설계되어야 한다는 점을 깨달았고,** Range Scan vs Index Scan의 차이를 실제로 경험하여 인덱스를 제대로 활용하는 법을 깨달았습니다.

### 6.4 성능 측정의 중요성

- `EXPLAIN` 명령어로 실행 계획 분석
- `SHOW PROFILES`로 마이크로초 단위 측정

**→ 위 명령어들을 통해서 가정보다는 실제 측정 결과**를 토대로 분석하는 것에 재미를 느꼈습니다.

**놀라운 성능 개선**

```
9.33초 → 3.60초 (61.4% 개선) → 0.002초 (99.9% 개선)
```

### 6.5 실무에서의 적용점

 **개발 프로세스 개선의 소중함을 깨달았습니다.** 대용량 데이터 시나리오 미리 고려했다면 어땠을까? 라는 생각이 들었습니다. 초반 설계부터 이런 고민을 했었다면 개발 시간을 단축시키고, 보다 더 최적화와 관련된 공부를 할 수 있었을 것 같습니다. 하지만, 이러한 과정을 통해서 데이터베이스 쿼리 최적화 지식의 필요성을 여실히 느끼게 되어 뜻깊은 시간이 된 것 같습니다.

 ****또한, **사용자 경험의 중요성**을 깨달았습니다. 이 성능 개선은 9초 정도의 문장 조회 시간이 사용자 이탈로 직결될 수도 있겠다는 생각에서부터 시작했습니다. 즉, 백엔드 성능이 UX에도 직접적인 영향을 줄 수 있다는 점을 깨달았고, 성능이 기능 구현만큼 중요하다는 점을 다시금 깨달았습니다.

## 7. 결론

 이 프로젝트를 통해 **"작동하는 코드"와 "좋은 코드"는 완전히 다르다**는 것을 깨달았습니다. 크게 3가지로 정리해보면 다음과 같습니다.

- 데이터베이스 쿼리 최적화 지식의 필요성
- 프로파일링 측정 기반의 개선의 중요성
- 사용자 경험을 항상 염두에 둔 개발의 중요성

 앞으로는 개발 초기부터 성능을 고려한 설계를 하고, 지속적인 성능 테스트를 통해 문제를 조기에 발견하는 개발 습관을 가지도록 노력하겠습니다.

## 8. Reference

[[10분 테코톡] 초코칩&로키의 인덱스와 스캔 튜닝](https://www.youtube.com/watch?v=_UI8YDU_mfg)

[MySQL의 Using temporary, Using filesort (+ 정렬 방식) 정리!](https://seongonion.tistory.com/158)

[Real MySQL [7-17] 쿼리 작성 및 최적화 - ORDER BY](https://weicomes.tistory.com/322)

[MySQL. 'Select tables optimized away' vs 'Using index'](https://neunggu.tistory.com/42)

[[MySQL] INDEX 최적화 - 2 (feat. 커버링, 컨디션 푸시다운)](https://guard-x100.tistory.com/23)