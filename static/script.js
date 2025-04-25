// 검색 중 로딩 스피너 보이기
function showSpinner() {
    document.querySelector('.spinner').style.display = 'block';  // 스피너 보이기
}

// 검색 중 로딩 스피너 숨기기
function hideSpinner() {
    document.querySelector('.spinner').style.display = 'none';  // 스피너 숨기기
}

// 검색 폼 제출 시 실행되는 함수
function searchTroubleshooting(event) {
    event.preventDefault();  // 폼의 기본 제출을 막고
    
    showSpinner();  // 검색 시작 시 스피너 보이기

    // 실제 검색 로직을 처리하는 부분 (여기서는 2초 대기 예시)
    setTimeout(function() {
        hideSpinner();  // 검색 완료 후 스피너 숨기기
        alert("검색 완료!");
        // 이후 검색 결과 처리 (예: 서버에서 검색 결과 받아오기)
    }, 2000);  // 2초 후에 스피너를 숨깁니다
}
