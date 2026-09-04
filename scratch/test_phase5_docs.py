"""
Verification Test Suite for IGIRS AI Phase 5:
Document Intelligence & Local RAG Engine (PDFs, Notes, Resumes, Code).
"""
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Set UTF-8 encoding for console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pypdf
from tools.document_engine import DocumentEngine
from assistant import IGIRSAssistant
from gui.api_bridge import DesktopApiBridge

def create_sample_pdf(file_path: Path):
    """Generates a minimal 2-page test PDF with pypdf containing font dictionaries."""
    writer = pypdf.PdfWriter()
    
    pages_data = [
        [
            "Quantum Computing and Entanglement Lecture Notes",
            "Definition: Quantum entanglement is a phenomenon where quantum particles",
            "become interconnected such that the state of one instantly influences the other.",
            "Qubits can exist in superposition: alpha|0> + beta|1> where alpha^2 + beta^2 = 1."
        ],
        [
            "Chapter 2 Key Takeaways and Quantum Algorithms",
            "Shor algorithm provides exponential speedup for integer factorization.",
            "Grover algorithm provides quadratic speedup for unstructured database search.",
            "Quantum teleportation allows transferring quantum states between distant qubits."
        ]
    ]

    for text_lines in pages_data:
        page = writer.add_blank_page(width=612, height=792)
        stream_data = "BT\n/F1 12 Tf\n50 700 Td\n"
        for line in text_lines:
            stream_data += f"({line}) Tj\n0 -25 Td\n"
        stream_data += "ET\n"

        c = pypdf.generic.DecodedStreamObject()
        c.set_data(stream_data.encode("latin-1"))

        font_dict = pypdf.generic.DictionaryObject({
            pypdf.generic.NameObject("/Type"): pypdf.generic.NameObject("/Font"),
            pypdf.generic.NameObject("/Subtype"): pypdf.generic.NameObject("/Type1"),
            pypdf.generic.NameObject("/BaseFont"): pypdf.generic.NameObject("/Helvetica"),
        })
        res_dict = pypdf.generic.DictionaryObject({
            pypdf.generic.NameObject("/Font"): pypdf.generic.DictionaryObject({
                pypdf.generic.NameObject("/F1"): font_dict
            })
        })
        page[pypdf.generic.NameObject("/Resources")] = res_dict
        page[pypdf.generic.NameObject("/Contents")] = c

    with open(file_path, "wb") as f:
        writer.write(f)

def run_tests():
    print("=" * 65)
    print("📚 IGIRS AI — Phase 5 Document Intelligence & RAG Verification")
    print("=" * 65)

    test_dir = Path("scratch/test_docs")
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create sample documents
    print("\n[1/6] Generating test documents (PDF, Code, Resume, Notes)...")
    
    pdf_path = test_dir / "quantum_lecture.pdf"
    create_sample_pdf(pdf_path)
    print(f"  • Created sample lecture PDF: {pdf_path.name}")

    py_path = test_dir / "math_utils.py"
    py_content = """# Math utilities for IGIRS
def fibonacci(n: int) -> int:
    \"\"\"Calculates the nth Fibonacci number efficiently.\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def is_prime(n: int) -> bool:
    \"\"\"Checks if a number is prime.\"\"\"
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
"""
    with open(py_path, "w", encoding="utf-8") as f:
        f.write(py_content)
    print(f"  • Created sample Python code file: {py_path.name}")

    resume_path = test_dir / "joshua_resume.txt"
    resume_content = """JOSHUA - AI & FULL-STACK SOFTWARE ENGINEER
Email: joshua@example.com | LinkedIn: linkedin.com/in/joshua

PROFESSIONAL SUMMARY
Experienced AI software engineer specializing in speech-to-speech personal assistants,
multimodal computer vision, and local desktop automation on Windows.

TECHNICAL SKILLS
- Languages: Python, JavaScript, TypeScript, C++, SQL
- AI/ML Frameworks: NVIDIA NIM, OpenAI Whisper, Edge-TTS, PyTorch
- Systems & Desktop: Win32 API, PyWebView, DirectSound, Multithreading

KEY PROJECTS
1. IGIRS AI Assistant: Built autonomous desktop assistant with real-time speech,
   Win32 hardware automation, Spotify/YouTube controls, and multimodal vision.
"""
    with open(resume_path, "w", encoding="utf-8") as f:
        f.write(resume_content)
    print(f"  • Created sample Resume text: {resume_path.name}")
    print("  [OK] Test documents ready.")

    # 2. Ingestion & Classification Test
    print("\n[2/6] Ingesting & Classifying Documents...")
    engine = DocumentEngine()
    engine.clear_all()

    res_pdf = engine.ingest_file(source=pdf_path, filename=pdf_path.name)
    print(f"  • PDF Ingest: Category={res_pdf['category']}, Pages={res_pdf['total_pages']}, Chunks={res_pdf['total_chunks']}")
    assert res_pdf["status"] == "success", "PDF ingest failed!"

    res_code = engine.ingest_file(source=py_path, filename=py_path.name)
    print(f"  • Code Ingest: Category={res_code['category']}, Chunks={res_code['total_chunks']}")
    assert res_code["category"] == "code", f"Expected 'code' category, got {res_code['category']}"

    res_resume = engine.ingest_file(source=resume_path, filename=resume_path.name)
    print(f"  • Resume Ingest: Category={res_resume['category']}, Words={res_resume['total_words']}")
    assert res_resume["category"] == "resume", f"Expected 'resume' category, got {res_resume['category']}"
    print("  [OK] Ingestion and auto-classification verified.")

    # 3. Chunk Ranking & Retrieval Test
    print("\n[3/6] Testing BM25 / Keyword Retrieval Scoring...")
    ranked = engine._rank_chunks("What is quantum entanglement and superposition?")
    print(f"  • Top chunk matches found: {len(ranked)}")
    assert len(ranked) > 0, "No chunks retrieved for query!"
    top_doc = ranked[0]
    print(f"  • Best match: {top_doc['filename']} (Score: {top_doc['score']:.2f})")
    assert "quantum" in top_doc["text"].lower() or "quantum" in top_doc["filename"].lower()
    print("  [OK] Retrieval scoring verified.")

    # 4. Live RAG Q&A Test
    print("\n[4/6] Testing Live RAG Question Answering with NVIDIA NIM...")
    q_res = engine.answer_query("What are the key technical skills and projects on Joshua's resume?")
    print(f"  • Answer Status: {q_res['status']}")
    print(f"  • Answer Preview:\n    {q_res['answer'][:250]}...")
    assert len(q_res["answer"]) > 20, "Empty RAG answer returned!"
    assert q_res.get("citations"), "Missing citations in RAG response!"
    print(f"  • Citations: {q_res['citations']}")
    print("  [OK] RAG Q&A verified.")

    # 5. Live Document Summarization Test
    print("\n[5/6] Testing Live Document Executive Summarization...")
    summary_res = engine.summarize_document(doc_id=res_resume["id"])
    print(f"  • Summary Status: {summary_res['status']}")
    print(f"  • Summary Preview:\n    {summary_res['summary'][:220]}...")
    assert summary_res["status"] == "success", "Summarization failed!"
    print("  [OK] Document summarization verified.")

    # 6. Desktop GUI Bridge Test
    print("\n[6/6] Testing Desktop GUI Bridge Document Methods...")
    assistant = IGIRSAssistant()
    bridge = DesktopApiBridge(assistant)

    doc_list = bridge.get_documents()
    print(f"  • Bridge get_documents returned: {len(doc_list)} items")
    assert len(doc_list) >= 3, "Bridge did not return all indexed documents!"

    bridge_query = bridge.query_document("How does the fibonacci function work in math_utils?", speak_response=False)
    print(f"  • Bridge query result status: {bridge_query['status']}")
    print(f"  • Bridge query answer preview: {bridge_query['answer'][:180]}...")
    assert bridge_query["status"] == "success", "Bridge query_document failed!"
    print("  [OK] Desktop GUI Bridge methods verified.")

    print("\n" + "=" * 65)
    print("🎉 ALL PHASE 5 DOCUMENT RAG CHECKS PASSED!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
