<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ULVAC Trouble Shooting Program</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    <div class="container">
        <h1>ULVAC Trouble Shooting Program</h1>

        <!-- 트러블 등록 폼 -->
        <form method="POST" action="/" id="troubleForm" enctype="multipart/form-data">
            <label for="trouble_date">발생일(発生日)</label>
            <input type="date" id="trouble_date" name="trouble_date" required>
            <label for="device_code">장치 지번(装置指番)</label>
            <input type="text" id="device_code" name="device_code" placeholder="예) ME24-4504-0" required>
            <label for="device_name">장치명(装置名)</label>
            <input type="text" id="device_name" name="device_name" required>
            <label for="user_name">성명(報告者)</label>
            <input type="text" id="user_name" name="user_name" required>
            <label for="trouble_text">트러블 증상(Trouble内容)</label>
            <textarea id="trouble_text" name="trouble_text" rows="2" required></textarea>
            <label for="solution">해결 방법(解決方法)</label>
            <textarea id="solution" name="solution" rows="2" required></textarea>
            <label for="category">카테고리(カテゴリー)</label>
            <select id="category" name="category">
                <option value="">선택 안 함</option>
                <option value="전원 또는 제품 불량">전원 또는 제품 불량</option>
                <option value="케이블 배선 불량">케이블 배선 불량</option>
                <option value="조립 불량">조립 불량</option>
                <option value="기타">기타</option>
            </select>
            <label for="tags">해쉬태그 (쉼표로 구분)</label>
            <input type="text" id="tags" name="tags">
            <label for="image">사진 첨부(휴대폰용)</label>
            <input type="file" id="image" name="image" accept=".jpg,.jpeg,.png" onchange="checkFile(this)">
            
            <!-- 클립보드로 이미지 붙여넣기 -->
            <div id="paste-container">
                <label>사진 첨부(노트북용) ※ Cannot upload images over 2mb, use clipboard capture</label>
                <div id="paste-area" tabindex="0">Window key+shift+S로 캡쳐 후, Ctrl+V로 사진첨부</div>
                <div id="image-preview-container" style="display:none;">
                    <img id="image-preview" src="" alt="미리보기" style="max-width:100%; max-height:200px; margin-top:10px;">
                    <button type="button" id="remove-image" onclick="removeClipboardImage()">이미지 제거</button>
                </div>
                <input type="hidden" id="clipboard-image-data" name="clipboard_image_data">
            </div>
            
            <input type="submit" value="등록(登録)">
        </form>

        <!-- 검색 폼 -->
        <form method="POST" action="/search">
            <label for="search_query">트러블 검색(Trouble検索)</label>
            <input type="text" id="search_query" name="search_query" placeholder="트러블 증상명 검색">
            <label for="search_tags">해쉬태그</label>
            <input type="text" id="search_tags" name="search_tags" placeholder="트러블 해시태그 검색">
            <button type="submit">검색</button>
        </form>
    </div>

    <script>
        // 클립보드 이미지 처리
        document.addEventListener('DOMContentLoaded', function() {
            const pasteArea = document.getElementById('paste-area');
            const imagePreviewContainer = document.getElementById('image-preview-container');
            const imagePreview = document.getElementById('image-preview');
            const clipboardImageData = document.getElementById('clipboard-image-data');
            const fileInput = document.getElementById('image');

            pasteArea.addEventListener('click', function() {
                pasteArea.focus();
            });

            document.addEventListener('paste', function(e) {
                handlePaste(e);
            });

            pasteArea.addEventListener('paste', function(e) {
                handlePaste(e);
            });

            function handlePaste(e) {
                const items = e.clipboardData.items;
                let imageItem = null;

                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        imageItem = items[i];
                        break;
                    }
                }

                if (imageItem) {
                    e.preventDefault();
                    const blob = imageItem.getAsFile();

                    compressImage(blob, 20, function(compressedDataUrl) {
                        imagePreview.src = compressedDataUrl;
                        imagePreviewContainer.style.display = 'block';
                        clipboardImageData.value = compressedDataUrl;
                        pasteArea.innerHTML = '이미지가 붙여넣어졌습니다';
                    });
                }
            }

            function compressImage(blob, maxSizeMB, callback) {
                const img = new Image();
                const reader = new FileReader();
                reader.onload = function(event) {
                    img.src = event.target.result;
                };

                img.onload = function() {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    let width = img.width;
                    let height = img.height;
                    const maxBytes = maxSizeMB * 1024 * 1024;

                    if (blob.size > maxBytes) {
                        const scale = Math.sqrt(maxBytes / blob.size) * 0.9;
                        width = Math.floor(width * scale);
                        height = Math.floor(height * scale);
                    }

                    canvas.width = width;
                    canvas.height = height;
                    ctx.drawImage(img, 0, 0, width, height);

                    let quality = 0.9;
                    let dataUrl;
                    do {
                        dataUrl = canvas.toDataURL('image/jpeg', quality);
                        quality -= 0.1;
                    } while (dataUrl.length > maxBytes && quality > 0.1);

                    callback(dataUrl);
                };

                reader.readAsDataURL(blob);
            }

            function removeClipboardImage() {
                const pasteArea = document.getElementById('paste-area');
                const imagePreviewContainer = document.getElementById('image-preview-container');
                const imagePreview = document.getElementById('image-preview');
                const clipboardImageData = document.getElementById('clipboard-image-data');
                
                imagePreview.src = '';
                imagePreviewContainer.style.display = 'none';
                clipboardImageData.value = '';
                pasteArea.innerHTML = '여기에 이미지를 붙여넣으세요';
            }
        });
    </script>
</body>
</html>
