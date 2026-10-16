# Git Branch Rules

이 프로젝트의 브랜치 생성 및 PR 규칙입니다.

## main 브랜치

- `main`, `dev` 브랜치에 직접 push는 금지되어 있습니다.
- 모든 변경 사항은 별도 브랜치에서 작업 후 PR(Pull Request)을 통해 병합합니다.
- PR의 경우 현재 최소 1명의 허가가 필요하고, 따라서 이 때 코드리뷰를 진행할 예정입니다.

## 브랜치 명명 규칙

```
<type>/<설명>
```

`type`은 [커밋 규칙](git_commit_rule.md)의 type과 동일하게 사용합니다.

| Type       | 설명                    |
|------------|-------------------------|
| `feat`     | 새로운 기능 개발        |
| `fix`      | 버그 수정               |
| `chore`    | 빌드, 설정, 스크립트 등 |
| `refactor` | 코드 구조 개선          |
| `docs`     | 문서 작업               |
| `test`     | 테스트 코드 작업        |
| `style`    | 포맷팅 등               |

`설명`은 영어 소문자와 하이픈(`-`)으로 작성합니다.

예시:
```
feat/prompt-translation
fix/image-generate-timeout
chore/change-service-ports
docs/git-branch-rules
```

## 작업 흐름

1. `main` 기준으로 새 브랜치 생성
2. 기능 단위로 커밋하며 작업
3. 원격에 push 후 PR 생성 (`main` ← 작업 브랜치)
4. 리뷰 및 승인 후 병합
5. 병합된 브랜치는 삭제

## 기타

- 하나의 브랜치는 하나의 기능/이슈 단위로 생성 (여러 작업을 한 브랜치에 섞지 않음)
