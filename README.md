# 판매량 추이 대시보드 (sooptore / e-ncp)

10분마다 GitHub Actions가 e-ncp 상품 옵션 API를 호출해서
`data/history.json`에 기록을 쌓고, GitHub Pages로 배포되는 `index.html`이
그 데이터를 그래프로 보여줍니다.

## 1. 저장소에 올리기

이 폴더 전체를 새 GitHub 저장소에 그대로 올리세요.

```
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/<your-id>/<repo>.git
git push -u origin main
```

## 2. GitHub Pages 켜기

저장소 Settings → Pages → Build and deployment
→ Source: `Deploy from a branch` → Branch: `main` / `/(root)` 선택 후 저장.

몇 분 뒤 `https://<your-id>.github.io/<repo>/` 로 접속하면 대시보드가 보입니다.

## 3. Actions 권한 확인

Settings → Actions → General → Workflow permissions에서
**"Read and write permissions"** 로 되어 있어야
워크플로우가 `data/history.json`을 커밋/푸시할 수 있습니다.

## 4. 데이터 구조

`/products/{id}/options` 응답은 옵션 객체들의 배열입니다.

```json
[
  {
    "optionNo": 514748023,
    "label": "상품",
    "value": "일상 ver.세트",
    "addPrice": 0,
    "saleCnt": 430,
    "stockCnt": 9805
  },
  ...
]
```

`fetch_sales.py`는 모든 옵션의 `saleCnt`를 합산해서 `sales_value`(전체 판매량)로,
`stockCnt`를 합산해서 `stock_value`(전체 재고)로 기록하고, 옵션별 상세도
`options` 배열에 그대로 남겨둡니다. 옵션 하나만 있는 상품이면 합계 = 그 옵션의
`saleCnt`와 동일합니다.

## 5. API가 계속 400을 반환한다면

- `scripts/fetch_sales.py`의 `HEADERS`에서 `Referer`/`Origin`이
  실제 상품 페이지(`https://sooptore.sooplive.com/products/133850457`)와
  일치하는지 확인하세요.
- 그래도 안 되면 브라우저 개발자도구(F12) → Network 탭에서 해당 요청을 찾아
  `Request Headers`를 그대로 복사해서 `HEADERS`에 반영하세요.
- 쿠키 기반 인증이 필요한 경우, 쿠키 값을 GitHub Actions의
  **Secrets**(Settings → Secrets and variables → Actions)에 등록하고
  스크립트에서 `os.environ`으로 읽어 헤더에 추가하면 됩니다.

## 파일 구조

```
.
├── .github/workflows/update-sales.yml   # 10분마다 실행되는 워크플로우
├── scripts/fetch_sales.py               # API 호출 + 데이터 누적 스크립트
├── data/history.json                    # 누적 저장되는 시계열 데이터
├── index.html                           # GitHub Pages 대시보드
└── README.md
```
