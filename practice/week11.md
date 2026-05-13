# Week 11 실습

## 오늘 한 것
- PyInstaller 설치 및 빌드
- resource_path() 함수 추가
- --add-data 옵션으로 에셋 포함
- MyGame.exe 실행 확인

## resource_path() 를 써야 하는 이유
.exe로 빌드하면 파일들이 임시폴더로 압축 해제되는데,
이때 상대경로가 깨져서 이미지/사운드가 안 뜬다.
resource_path()는 개발 중(Thonny)과 빌드 후(.exe) 환경을
자동으로 판단해서 항상 올바른 경로를 반환해준다.

## 빌드 명령어
pyinstaller --onefile --windowed --add-data "assets;assets" --name=MyGame main.py

## AI 활용 내역
- PyInstaller 설치 및 빌드 순서 안내
- resource_path() 함수 설명 및 적용 위치 안내
- 경로 문제 원인과 해결 방법 설명