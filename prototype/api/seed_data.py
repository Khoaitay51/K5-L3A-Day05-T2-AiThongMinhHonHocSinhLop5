import asyncio
from database import get_db_pool, init_db, get_embedding

DOCS = [
    {
        "section_code": "§3.1",
        "title": "Trung bình cộng",
        "content": "Tổng các giá trị chia cho số giá trị. Trung bình bị kéo mạnh bởi giá trị ngoại lai.",
        "is_active_assignment": False
    },
    {
        "section_code": "§3.2",
        "title": "Trung vị",
        "content": "Giá trị đứng giữa khi sắp xếp dữ liệu tăng dần. Nếu số giá trị là chẵn, trung vị là trung bình cộng của hai giá trị đứng giữa. Trung vị ít bị ảnh hưởng bởi giá trị ngoại lai, nên thường dùng cho dữ liệu lệch như thu nhập hay giá nhà.",
        "is_active_assignment": False
    },
    {
        "section_code": "§3.3",
        "title": "Phương sai và độ lệch chuẩn",
        "content": "Phương sai đo mức độ phân tán của dữ liệu quanh trung bình. Độ lệch chuẩn là căn bậc hai của phương sai, có cùng đơn vị với dữ liệu. Vì là căn bậc hai, độ lệch chuẩn luôn nhỏ hơn phương sai.",
        "is_active_assignment": False
    },
    {
        "section_code": "§3.4",
        "title": "Giá trị ngoại lai",
        "content": "Giá trị khác hẳn phần lớn dữ liệu. Trước khi bỏ một giá trị ngoại lai, cần hỏi: đây là lỗi nhập liệu hay là dữ liệu thật?",
        "is_active_assignment": False
    },
    {
        "section_code": "§3.5",
        "title": "Bài tập 3 (Đang mở - Hạn 13/11/2026 23:59)",
        "content": "Lương tháng của 8 nhân viên một phòng (triệu đồng, dựng): 9, 10, 10, 11, 12, 12, 13, 45. (a) Tính trung bình và trung vị. (b) Con số nào mô tả 'lương điển hình' của phòng tốt hơn? Vì sao?",
        "is_active_assignment": True
    },
    {
        "section_code": "BT2",
        "title": "Bài tập 2 (Đã hết hạn - Có đáp án)",
        "content": "Hạn 06/11/2026 23:59. Đã hết hạn. Đáp án công bố 07/11: 'Trung bình cộng của 4, 8, 6, 5, 7 là 6.'",
        "is_active_assignment": False
    },
    {
        "section_code": "SYLLABUS",
        "title": "Đề cương các buổi học",
        "content": "Buổi đã mở: 1, 2, 3 (Thống kê mô tả). Các buổi sau chưa mở: 4 Trực quan hoá dữ liệu · 5 Xác suất cơ bản · 6 Phân phối chuẩn · 7 Kiểm định giả thuyết và p-value · 8 Hồi quy tuyến tính · 9 Làm sạch dữ liệu · 10 Dự án cuối khoá.",
        "is_active_assignment": False
    }
]

async def seed():
    await init_db()
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM course_documents;")
        if count > 0:
            print(f"Database already seeded with {count} documents.")
            return

        print("Seeding course documents into pgvector database...")
        for doc in DOCS:
            embedding = await get_embedding(f"{doc['title']}: {doc['content']}")
            await conn.execute("""
                INSERT INTO course_documents (section_code, title, content, is_active_assignment, embedding)
                VALUES ($1, $2, $3, $4, $5);
            """, doc["section_code"], doc["title"], doc["content"], doc["is_active_assignment"], embedding)
            print(f"  + Seeded {doc['section_code']}: {doc['title']}")

        print("Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())

