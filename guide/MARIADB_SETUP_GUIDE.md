# MariaDB 설치 가이드 (macOS)

MariaDB 10.11을 macOS에 설치하는 간단한 가이드입니다.

> **📚 데이터베이스 전체 설정 가이드는 [DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)를 참고하세요.**

---

## 🐳 Docker로 설치 (권장)

### 1. Docker Desktop 설치

[Docker Desktop for Mac](https://www.docker.com/products/docker-desktop) 다운로드 및 설치

### 2. MariaDB 컨테이너 실행

```bash
# docker-compose 사용 (프로젝트에 이미 설정됨)
docker-compose up -d db_dev

# 또는 직접 실행
docker run -d \
  --name mariadb-dongwon \
  -p 3307:3306 \
  -e MARIADB_ROOT_PASSWORD=12345 \
  -e MARIADB_DATABASE=dongwon \
  -e MARIADB_USER=test \
  -e MARIADB_PASSWORD=12345 \
  -v mariadb-dongwon-data:/var/lib/mysql \
  mariadb:10.11
```

### 3. 확인

```bash
# 컨테이너 상태 확인
docker ps

# MariaDB 접속 테스트
docker exec -it db_dev mysql -u root -p12345
```

### 장점

- ✅ 간단하고 빠른 설치
- ✅ 시스템 환경 오염 없음
- ✅ 쉬운 삭제 및 재설치
- ✅ 버전 관리 용이

---

## 🔧 Homebrew로 설치

### 1. Homebrew 설치 (없는 경우)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. MariaDB 10.11 설치

```bash
brew install mariadb@10.11
```

### 3. PATH 설정

**Apple Silicon (M1/M2/M3):**

```bash
echo 'export PATH="/opt/homebrew/opt/mariadb@10.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Intel Mac:**

```bash
echo 'export PATH="/usr/local/opt/mariadb@10.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 4. MariaDB 시작

```bash
brew services start mariadb@10.11
```

### 5. Root 비밀번호 설정

```bash
mysql -u root

# MariaDB 프롬프트에서:
ALTER USER 'root'@'localhost' IDENTIFIED BY '12345';
FLUSH PRIVILEGES;
EXIT;
```

### 6. 데이터베이스 생성

```bash
mysql -u root -p

# MariaDB 프롬프트에서:
CREATE DATABASE dongwon CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

---

## 🔍 유용한 명령어

### Docker 명령어

```bash
# 시작/중지/재시작
docker start db_dev
docker stop db_dev
docker restart db_dev

# 상태 확인
docker ps

# 로그 확인
docker logs db_dev

# MariaDB 접속
docker exec -it db_dev mysql -u root -p12345

# 데이터베이스 확인
docker exec -i db_dev mysql -u root -p12345 -e "SHOW DATABASES;"
```

### Homebrew 명령어

```bash
# 서비스 관리
brew services start mariadb@10.11
brew services stop mariadb@10.11
brew services restart mariadb@10.11
brew services list

# MariaDB 접속
mysql -u root -p -P 3307
mysql -u root -p -P 3307 dongwon
```

---

## 🚨 트러블슈팅

### 1. "Can't connect to MySQL server"

```bash
# Docker
docker restart db_dev

# Homebrew
brew services restart mariadb@10.11
```

### 2. "Access denied for user 'root'"

비밀번호가 맞지 않습니다. Root 비밀번호를 재설정하세요.

### 3. "Port 3307 is already in use"

```bash
# 포트 사용 중인 프로세스 확인
lsof -i :3307

# 프로세스 종료
kill -9 <PID>
```

---

## 💡 GUI 도구 (선택)

MariaDB를 더 쉽게 관리하려면 GUI 도구를 사용하세요:

### DBeaver (무료, 추천)

```bash
brew install --cask dbeaver-community
```

### TablePlus (유료, 깔끔한 UI)

```bash
brew install --cask tableplus
```

---

## 📚 다음 단계

MariaDB 설치가 완료되었다면:

1. **[DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)** - 테이블 생성 및 전체 설정
2. **[PRISMA_STYLE_GUIDE.md](./PRISMA_STYLE_GUIDE.md)** - 모델 정의 및 DB Push
3. **[ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md)** - 환경 변수 설정

---

## 📖 참고 자료

- [MariaDB 공식 문서](https://mariadb.com/kb/en/)
- [Homebrew MariaDB](https://formulae.brew.sh/formula/mariadb@10.11)
- [Docker Hub - MariaDB](https://hub.docker.com/_/mariadb)

---

**작성일**: 2025-10-24  
**최종 수정**: 2025-10-24
