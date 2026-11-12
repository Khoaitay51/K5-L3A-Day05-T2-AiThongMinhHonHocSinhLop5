# Chạy demo Study Mode

1. Cấu hình PostgreSQL và `GEMINI_API_KEY` trong `.env` ở thư mục gốc. Dùng `.env.example` nếu cần tạo file mới.
2. Đặt `STUDY_TA_KEY` thành một mã riêng cho người đóng vai trợ giảng. Đặt `STUDY_DEMO_NOW=2026-11-13T23:20:00+07:00` để tái hiện cảnh còn 39 phút. Để trống biến thời gian khi muốn dùng đồng hồ thực.
3. Chạy `docker compose up --build`, rồi mở [Study Mode](http://localhost:8000). Trang này là bản demo chính. [Bản HTML tĩnh](index.html) minh họa ba mức tự chủ từ phiên bản trước.

## Hai ca trong spec

- **#6.** Chọn **Gợi ý Bài tập 3**, gửi câu hỏi rồi mở thẻ hướng dẫn. Gửi hai giá trị đã chọn để mở bước 2. Lời giải chỉ xuất hiện từ 23:59 ngày 13/11. Có thể xem trước câu hỏi, xác nhận gửi TA và hủy trước khi TA mở ticket.
- **#9.** Chọn **Đề xuất câu hỏi FAQ** rồi gửi. Học viên xem bản nháp, đoạn cần rà soát và trạng thái chờ duyệt. Trong tab **Trợ giảng**, nhập mã, đối chiếu §3.3, sửa câu trả lời nếu cần, xác nhận đã kiểm tra và bấm **Duyệt và đăng FAQ**. Quay lại tab học viên để xem thông báo và mục FAQ đã công khai.

Gemini hiểu câu hỏi, chọn công cụ và soạn nội dung dự thảo FAQ. FastAPI kiểm tra trạng thái bài tập và quyền duyệt, PostgreSQL lưu trạng thái. Phiên học viên dùng cookie của trình duyệt. Trợ giảng dùng mã truy cập demo. Khi chưa có khóa Gemini, chat báo cần cấu hình. Xem **Nhật ký công cụ** để kiểm tra Gemini đã gọi công cụ nào.

Swagger ở [trang tài liệu API](http://localhost:8000/docs). Các API hàng đợi và duyệt nhận mã trợ giảng qua header `X-TA-Key`.
