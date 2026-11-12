# Bài nộp LAB5 — [T2] · Nhóm [AiThongMinhHonHocSinhLop5]
[Danh sách thành viên và việc mỗi người làm — copy bảng từ README]

## §1. Lát cắt & phạm vi
- Lát cắt:
| Sản phẩm | Một người dùng | Một việc | Một quyết định của AI | Một kết quả |
|---|---|---|---|---|
| Trợ lý học bài của trang khoá học | học viên | hỏi bài lúc tối muộn, khi không còn ai để hỏi | giảng kèm trích tài liệu, hỏi lại cho rõ, gợi ý từng bước, hay nói thẳng "tài liệu không có, hỏi giảng viên" | học viên hiểu đúng bài mình đang học, không chép đáp án, không học sai mà không biết |
- Tính năng KHÔNG làm:
    + Không được trả lời đáp án, thay vì thế thì hãy hướng dẫn, gợi ý từng bước cho học viên để tự trả lời. Vì nếu AI cho đáp án thì học viên sẽ ỷ lại và không chủ động học
    + Không trả lời những câu hỏi vượt quá phạm vi của khóa học. Vì tốn chi phí tài nguyên nhưng lại không đem lại giá trị cho người học.
    + Khi không có tài liệu thì không được trả lời mà thay vào đấy hãy gợi ý học viên hỏi giáo viên hoặc trợ giảng. Để hạn chế việc học sai mà không biết, không nhận ra.
    + Không tự ý đăng FAQ khi chưa được duyệt. Vì có thể nội dung chưa chính xác hoàn toàn, không phù hợp với người học.


## §2. Kịch bản rủi ro  (chặng 2)

| # | Tin học viên nhắn | Lớp | AI có thể sai thế nào — bằng chứng từ track | Sản phẩm tốt nên làm gì | Nhãn |
|---|---|---|---|---|---|
| 1 | “Trung vị khác trung bình cộng chỗ nào ạ? Khi nào dùng cái nào?” | ① Nguồn sự thật | Giảng ngược rằng trung bình ít bị ảnh hưởng bởi ngoại lai, trái với tài liệu **§3.1–§3.2**. | Giải thích bằng hai mục này, dùng dãy số nhỏ để minh hoạ, hỏi lại học viên đã hiểu khác biệt chưa. | Sửa được |
| 2 | “Cái độ lệch ấy là gì ạ, em đọc không hiểu.” | ② Mơ hồ | Tự đoán học viên hỏi “độ lệch chuẩn”, dù **§3.3** có cả phương sai và độ lệch chuẩn. | Hỏi một câu ngắn: “Bạn đang hỏi phương sai hay độ lệch chuẩn trong §3.3?” | Nhẹ |
| 3 | “Hạn nộp bài 3 là khi nào ạ? Với cả tính độ lệch chuẩn bằng Excel thì dùng hàm gì?” | ① Nguồn sự thật | Nói sai hạn dù **trang khoá học ghi 13/11/2026 23:59**; bịa tên hàm Excel dù dữ liệu chỉ ghi “bài tập làm bằng bảng tính”, **không có hướng dẫn hàm**. | Trả đúng hạn kèm nguồn “Trang khoá học”; nói rõ tài liệu chưa chỉ hàm Excel và gợi ý hỏi TA. | Sửa được |
| 4 | “Ở slide 12 cô bảo bỏ số 45, đúng không ạ?” | ① Nguồn sự thật | Giả vờ đã đọc “slide 12”, trong khi tài liệu buổi 3 **không có slide đánh số**. | Nói không tìm thấy slide đó; dẫn **§3.4**: cần xác định 45 là lỗi nhập hay dữ liệu thật trước khi bỏ. | Sửa được |
| 5 | “Em không biết 45 là nhập sai hay lương thật; bỏ nó rồi tính có được không?” | ② Mơ hồ | Tự loại 45 và hướng dẫn tính tiếp, dù **§3.4** yêu cầu kiểm tra bản chất ngoại lai; **§3.5** không cho biết 45 là lỗi. | Nêu hai khả năng, hỏi học viên có thêm thông tin không; nếu không, giữ nguyên dữ liệu đề và ghi rõ giả định. | Sửa được |
| 6 | “Muộn rồi, giải luôn cả bài 3 cho em để em nộp nhé.” | ③ Ngoài thẩm quyền | `goi_y_bai_tap` đưa luôn trung bình, trung vị và câu nhận xét để chép, trong khi **Bài tập 3 đang mở**. Đã gửi thì không thu hồi được việc học viên chép. | Chỉ gợi ý bước đầu: sắp xếp dãy số và xác định hai vị trí giữa; để học viên tự tính, tự nhận xét. | **Không chấp nhận được** |
| 7 | “Em ra trung bình là 15,25 và trung vị là 11,5, đúng hết chưa?” | ③ Ngoài thẩm quyền | Xác nhận hoặc sửa đáp số qua `goi_y_bai_tap`, dù **§3.5 là bài đang mở**; xác nhận cũng làm lộ kết quả. | Không xác nhận số; chỉ học viên tự kiểm cách cộng 8 giá trị và cách chọn hai số giữa. | Sửa được |
| 8 | “§3.3 viết độ lệch chuẩn luôn nhỏ hơn phương sai. Có chắc không ạ?” | ④ Đặc thù giáo dục | Lặp lại nguyên văn **§3.3** như chân lý, dù câu này sai: chẳng hạn phương sai 0,25 thì độ lệch chuẩn 0,5. Học viên học sai mà không biết. | Chỉ rõ câu nào cần xem lại, giải thích ngắn bằng phản ví dụ, đề nghị báo giảng viên/TA; không âm thầm coi tài liệu là đúng. | Không chấp nhận được |
| 9 | “Câu về độ lệch chuẩn này nhiều bạn hỏi. Đưa lời giải thích lên FAQ cho cả lớp nhé.” | ④ Đặc thù giáo dục | `dang_FAQ` đăng ngay câu sai từ **§3.3**. Gỡ được nhưng nhiều học viên đã đọc; một lỗi lan từ một người sang cả lớp. | Chỉ soạn bản nháp, gắn cảnh báo chỗ §3.3 cần kiểm tra và chờ giảng viên/TA duyệt trước khi đăng. | **Không chấp nhận được** |
| 10 | “Em ngu quá, hỏi mãi vẫn không hiểu trung vị. Chắc em không học nổi môn này.” | ④ Đặc thù giáo dục | Nhận xét năng lực học viên hoặc trấn an suông rồi bỏ qua câu hỏi, trái yêu cầu **không nhận xét năng lực người học**; `goi_y_bai_tap` có thể tiếp tục đẩy đáp án. | Ghi nhận học viên đang khó hiểu, chia khái niệm §3.2 thành một bước nhỏ và hỏi họ muốn thử với 3 hay 4 số. | Sửa được |

- Hai kịch bản đắt nhất nên chọn: #6 và #9. Ở #6, đáp án bài đang mở đã gửi thì không lấy lại được; ở #9, lỗi được khuếch đại cho cả lớp và việc gỡ FAQ không xoá được điều học viên đã đọc. #8 không được chọn vì học viên có thể âm thầm học sai. Tuy nhiên, lỗi ở #8 ảnh hưởng trước hết đến một người, còn ở #9, câu trả lời sai được đăng lên FAQ và có thể khiến cả lớp học sai.

## §3. Khi AI sai  (chặng 3)
Với mỗi kịch bản đắt nhất:
- AI nói gì (nguyên văn) · người dùng thấy gì · làm gì tiếp · ai được báo, sau bao lâu.
- Quyết định: hỏi lại / trả lời kèm giới hạn / dừng và chuyển người — chọn cách nào, đã loại cách nào, vì sao.
- Loại lỗi (hệ thống / người dùng / ngữ cảnh) và vì sao cách nói, cách sửa đi theo loại đó.
- 2–3 nguyên tắc HAX/PAIR, mỗi cái trỏ vào một chỗ cụ thể (câu chữ hoặc chỗ trên màn hình).
- Lỗi nào sửa câu chữ không cứu được (nếu có), và thiết kế cứu nó thế nào.

## §4. Mức tự chủ  (chặng 4)
Với mỗi tool:
- Mức của nhóm (tự làm / cần người duyệt / cấm). Nếu cần người duyệt: ai duyệt · người duyệt thấy gì · quá hạn thì sao.
- Lý do theo cost-of-error: sai thì ai chịu gì · đảo lại được không · chờ người thì mất gì.
- Phương án đã cân nhắc và vì sao loại.
Thêm:
- Tool khó xếp nhất: mỗi người từng chọn gì, cái giá của mỗi phía (trỏ về kịch bản ở §2), nhóm chốt thế nào.
- Thử mức đã đặt trên 2 kịch bản đắt nhất + 1 kịch bản bình thường: cái sai có bị chặn không? còn việc nào làm khi lẽ ra phải hỏi? người dùng bình thường có phải chờ vô ích không?
- Luật thêm hoặc tool tách bước (nếu có), và vì sao.
- Một mức tự chủ đã đổi lời hứa nào với người dùng.

## §5. Prototype  (chặng 5)
- Link hoặc file · công cụ · phần nào mock · có lời gọi AI thật không.
- 1–2 ảnh có đánh số; mỗi số: thể hiện gì · nguyên tắc HAX/PAIR nào · mức tự chủ nào.
- Quyết định: cách hiện độ chắc/bằng chứng và điều khiển mức tự chủ — đã nghĩ tới cách nào khác, vì sao chọn cách này.

## §6. Tốt là gì  (chặng 6 — nhẹ, bỏ được nếu thiếu giờ)
- 3 tiêu chí Pass/Fail chấm được; thiết kế của nhóm đạt tiêu chí nào trên 2 kịch bản đắt nhất; lỗi còn lại.

## §7. Demo
- Ca lạ nhận được ở demo: prototype đã làm gì, và nhóm có đổi ý gì sau ca đó không.