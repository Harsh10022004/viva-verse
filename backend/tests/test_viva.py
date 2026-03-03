from io import BytesIO
from PyPDF2 import PdfWriter

def create_dummy_pdf(text: str) -> bytes:
    # A simple way to make a dummy PDF byte stream for tests
    from reportlab.pdfgen import canvas
    output = BytesIO()
    c = canvas.Canvas(output)
    c.drawString(100, 750, text)
    c.save()
    return output.getvalue()

def test_upload_empty_files(client):
    # Edge Case: No files
    res = client.post("/api/v1/upload")
    assert res.status_code == 422 # FastAPI validation error for missing field

def test_upload_invalid_file_format(client):
    # Edge Case: Uploading a .txt file instead of .pdf
    files = {"files": ("test.txt", b"Hello, world", "text/plain")}
    res = client.post("/api/v1/upload", files=files)
    assert res.status_code == 415
    assert "Only PDF files are accepted" in res.json()["detail"]

def test_upload_valid_pdf(client):
    # Happy Path 1
    pdf_bytes = create_dummy_pdf("This is a dummy PDF file with enough text to overcome the chunk checks. It must be quite long actually to pass the 15 words limit! We need to make it big.")
    files = {"files": ("test.pdf", pdf_bytes, "application/pdf")}
    res = client.post("/api/v1/upload", files=files)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["total_chunks"] >= 0

def test_upload_multiple_pdfs(client):
    # Happy Path 2: Multi-doc upload
    pdf_bytes1 = create_dummy_pdf("This is dummy document one. We need to create at least 15 words to ensure it isn't skipped. Hello world, software engineering is great!")
    pdf_bytes2 = create_dummy_pdf("This is dummy document two. We need to create at least 15 words to ensure it isn't skipped. Hello world, software engineering is great!")
    files = [
        ("files", ("test1.pdf", pdf_bytes1, "application/pdf")),
        ("files", ("test2.pdf", pdf_bytes2, "application/pdf")),
    ]
    res = client.post("/api/v1/upload", files=files)
    assert res.status_code == 200

def test_upload_blank_pdf(client):
    pdf_bytes = create_dummy_pdf("   ")
    files = {"files": ("blank.pdf", pdf_bytes, "application/pdf")}
    res = client.post("/api/v1/upload", files=files)
    assert res.status_code == 400
    assert "no readable text" in res.json()["detail"]

def test_upload_duplicate_pdf(client):
    pdf_bytes = create_dummy_pdf("We need to create at least 15 words to ensure it isn't skipped. Hello world, software engineering is great! ")
    files = [
        ("files", ("duplicate.pdf", pdf_bytes, "application/pdf")),
        ("files", ("duplicate.pdf", pdf_bytes, "application/pdf")),
    ]
    res = client.post("/api/v1/upload", files=files)
    assert res.status_code == 400
    assert "Duplicate file detected" in res.json()["detail"]

def test_upload_unrelated_docs(client):
    pdf_bytes1 = create_dummy_pdf("Medieval kings ruled nations and fought battles using swords. " * 20)
    pdf_bytes2 = create_dummy_pdf("Python is a popular programming language for developers and AI. " * 20)
    
    files = [
        ("files", ("history.pdf", pdf_bytes1, "application/pdf")),
        ("files", ("programming.pdf", pdf_bytes2, "application/pdf")),
    ]
    
    res = client.post("/api/v1/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "requires_confirmation"
    assert any("completely different topics" in w for w in data["warnings"])


def test_upload_conflicting_docs(client):
    textA = "Neural networks neural networks. They use gradients heavily. Neural networks focus on gradients. gradients gradients gradients."
    textB = "Neural networks neural networks. They only use populations. Neural networks focus on populations populations."
    
    pdf_bytes1 = create_dummy_pdf(textA * 5)
    pdf_bytes2 = create_dummy_pdf(textB * 5)
    
    files = [
        ("files", ("docA.pdf", pdf_bytes1, "application/pdf")),
        ("files", ("docB.pdf", pdf_bytes2, "application/pdf")),
    ]
    
    res = client.post("/api/v1/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "requires_confirmation"
    assert len(data["conflicts"]) > 0
    
    conflicts = data["conflicts"]
    topic = conflicts[0]["topic"] 
    
    confirm_res = client.post("/api/v1/confirm-upload", json={
        "upload_id": data["upload_id"],
        "priorities": { topic: ["docB.pdf", "docA.pdf"] }
    })
    
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "success"

def test_start_viva_no_docs(client):
    # Edge Case: Start viva when doc store is empty
    # Reset doc_store by sending bad upload
    try:
        client.post("/api/v1/upload", files={"files": ("file.txt", b"A", "text/plain")})
    except:
        pass
    
    # We must explicitly reset backend state for this test if it's dirty,
    # but let's assume it might or might not be empty. Better to ensure it's empty.
    from app.api.v1.routes import doc_store
    doc_store.chunks = []
    
    res = client.post("/api/v1/start-viva")
    assert res.status_code == 400
    assert "No documents loaded" in res.json()["detail"]

def test_start_viva_success(client):
    # Happy Path 3: Success generating questions
    pdf_bytes = create_dummy_pdf("We need a long document layout. " * 30)
    client.post("/api/v1/upload", files={"files": ("test.pdf", pdf_bytes, "application/pdf")})
    
    res = client.post("/api/v1/start-viva")
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert len(data["questions"]) > 0

def test_submit_answer_invalid_session(client):
    # Edge Case: Invalid Session ID
    res = client.post("/api/v1/submit-answer", json={
        "session_id": "invalid-session",
        "question_id": "123",
        "answer": "My answer"
    })
    assert res.status_code == 404
    assert res.json()["detail"] == "Session not found."

def test_submit_answer_invalid_question(client):
    # Edge Case: Invalid Question ID
    pdf_bytes = create_dummy_pdf("Knowledge " * 20)
    client.post("/api/v1/upload", files={"files": ("test.pdf", pdf_bytes, "application/pdf")})
    res_start = client.post("/api/v1/start-viva")
    sid = res_start.json()["session_id"]
    
    res = client.post("/api/v1/submit-answer", json={
        "session_id": sid,
        "question_id": "not-a-real-id",
        "answer": "My answer"
    })
    assert res.status_code == 404
    assert res.json()["detail"] == "Question not found in this session."

def test_submit_answer_empty_text(client):
    # Edge Case: Empty Answer
    pdf_bytes = create_dummy_pdf("Knowledge " * 20)
    client.post("/api/v1/upload", files={"files": ("test.pdf", pdf_bytes, "application/pdf")})
    res_start = client.post("/api/v1/start-viva")
    sid = res_start.json()["session_id"]
    qid = res_start.json()["questions"][0]["id"]
    
    res = client.post("/api/v1/submit-answer", json={
        "session_id": sid,
        "question_id": qid,
        "answer": "   "
    })
    assert res.status_code == 200
    assert res.json()["score"] == 0
    assert "No content was provided" in res.json()["critique"]

def test_submit_answer_success(client):
    # Happy Path 4: Submit a valid answer
    pdf_bytes = create_dummy_pdf("Knowledge " * 20)
    client.post("/api/v1/upload", files={"files": ("test.pdf", pdf_bytes, "application/pdf")})
    res_start = client.post("/api/v1/start-viva")
    sid = res_start.json()["session_id"]
    qid = res_start.json()["questions"][0]["id"]
    
    res = client.post("/api/v1/submit-answer", json={
        "session_id": sid,
        "question_id": qid,
        "answer": "This is a great dummy answer testing the backend!"
    })
    assert res.status_code == 200
    assert "score" in res.json()
    assert "critique" in res.json()

def test_finalize_invalid_session(client):
    # Edge case: finalize invalid session
    res = client.post("/api/v1/finalize", json={"session_id": "random"})
    assert res.status_code == 404

def test_finalize_no_answers(client):
    # Edge case: finalize before answering any questions
    pdf_bytes = create_dummy_pdf("Knowledge " * 20)
    client.post("/api/v1/upload", files={"files": ("test.pdf", pdf_bytes, "application/pdf")})
    res_start = client.post("/api/v1/start-viva")
    sid = res_start.json()["session_id"]
    
    res = client.post("/api/v1/finalize", json={"session_id": sid})
    assert res.status_code == 400
    assert res.json()["detail"] == "No answers submitted yet."

def test_finalize_success(client):
    # Happy path 5: finalize after answering
    pdf_bytes = create_dummy_pdf("Knowledge is power. It allows humans to achieve impossible things. " * 5)
    client.post("/api/v1/upload", files={"files": ("test.pdf", pdf_bytes, "application/pdf")})
    res_start = client.post("/api/v1/start-viva")
    sid = res_start.json()["session_id"]
    qid = res_start.json()["questions"][0]["id"]
    
    client.post("/api/v1/submit-answer", json={
        "session_id": sid,
        "question_id": qid,
        "answer": "This is true."
    })
    
    res = client.post("/api/v1/finalize", json={"session_id": sid})
    assert res.status_code == 200
    assert "overall_score" in res.json()
    assert "topic_mastery" in res.json()
