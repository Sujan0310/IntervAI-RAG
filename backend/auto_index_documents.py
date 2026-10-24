"""
Auto-index documents from knowledge base folder on startup
This script automatically processes and indexes all documents in the knowledge_base folder
"""
import os
from pathlib import Path
from app.rag.ingestion.document_processor import DocumentProcessor
from app.rag.chunking.chunker import TextChunker
from app.rag.retrieval.hybrid_retriever import HybridRetriever

# Initialize components
doc_processor = DocumentProcessor()
chunker = TextChunker()
retriever = HybridRetriever()

# Knowledge base folder structure
KNOWLEDGE_BASE_PATH = Path("./knowledge_base")

# Domain folders
DOMAINS = {
    "machine-learning": "Machine Learning & AI",
    "data-structures": "Data Structures & Algorithms",
    "web-development": "Web Development",
    "system-design": "System Design",
    "python": "Python Programming",
    "databases": "Databases & SQL",
    "cloud-devops": "Cloud & DevOps",
    "general": "General Interview Questions"
}


def create_knowledge_base_structure():
    """Create knowledge base folder structure if it doesn't exist"""
    print("Creating knowledge base folder structure...")
    
    for domain_folder in DOMAINS.keys():
        domain_path = KNOWLEDGE_BASE_PATH / domain_folder
        domain_path.mkdir(parents=True, exist_ok=True)
        
        # Create README in each folder
        readme_path = domain_path / "README.txt"
        if not readme_path.exists():
            with open(readme_path, "w") as f:
                f.write(f"Place {DOMAINS[domain_folder]} documents here\n")
                f.write(f"Supported formats: PDF, DOCX, TXT\n")
                f.write(f"Files will be automatically indexed on server startup\n")
    
    print(f"✅ Knowledge base structure created at: {KNOWLEDGE_BASE_PATH}")


def index_documents_from_folder():
    """
    Automatically index all documents from knowledge_base folder
    Organizes by domain subfolders
    """
    print("\n" + "="*60)
    print("AUTO-INDEXING KNOWLEDGE BASE DOCUMENTS")
    print("="*60)
    
    # Create folder structure if needed
    create_knowledge_base_structure()
    
    if not KNOWLEDGE_BASE_PATH.exists():
        print(f"⚠️  Knowledge base folder not found: {KNOWLEDGE_BASE_PATH}")
        return {"total_files": 0, "total_chunks": 0, "domains_processed": 0}
    
    total_files = 0
    total_chunks = 0
    all_chunks = []
    
    # Process each domain folder
    for domain_folder, domain_name in DOMAINS.items():
        domain_path = KNOWLEDGE_BASE_PATH / domain_folder
        
        if not domain_path.exists():
            continue
        
        # Find all supported files
        supported_extensions = ['.pdf', '.docx', '.txt']
        files = []
        for ext in supported_extensions:
            files.extend(domain_path.glob(f"*{ext}"))
        
        if not files:
            continue
        
        print(f"\n📁 Processing {domain_name} ({len(files)} files)...")
        
        for file_path in files:
            try:
                # Skip README files
                if file_path.name.startswith("README"):
                    continue
                
                print(f"   📄 {file_path.name}...", end=" ")
                
                # Process document
                processed_doc = doc_processor.process_document(str(file_path))
                
                # Chunk document
                chunks = chunker.chunk_text(
                    text=processed_doc['text'],
                    strategy="semantic",
                    metadata={
                        "file_name": file_path.name,
                        "domain": domain_folder,
                        "domain_name": domain_name,
                        "file_type": processed_doc['file_type'],
                        "source": "knowledge_base"
                    }
                )
                
                all_chunks.extend(chunks)
                total_files += 1
                total_chunks += len(chunks)
                
                print(f"✅ {len(chunks)} chunks")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    if all_chunks:
        print(f"\n🔄 Indexing {total_chunks} chunks from {total_files} files...")
        retriever.index_documents(all_chunks)
        print(f"✅ Successfully indexed {total_chunks} chunks!")
    else:
        print("\n⚠️  No documents found in knowledge base")
        print(f"   Add PDF, DOCX, or TXT files to: {KNOWLEDGE_BASE_PATH}")
    
    print("\n" + "="*60)
    print(f"INDEXING COMPLETE: {total_files} files, {total_chunks} chunks")
    print("="*60 + "\n")
    
    return {
        "total_files": total_files,
        "total_chunks": total_chunks,
        "domains_processed": len([d for d in DOMAINS.keys() if (KNOWLEDGE_BASE_PATH / d).exists()])
    }


def get_knowledge_base_stats():
    """Get statistics about indexed knowledge base"""
    stats = {
        "total_documents": 0,
        "by_domain": {}
    }
    
    for domain_folder, domain_name in DOMAINS.items():
        domain_path = KNOWLEDGE_BASE_PATH / domain_folder
        if domain_path.exists():
            supported_extensions = ['.pdf', '.docx', '.txt']
            files = []
            for ext in supported_extensions:
                files.extend(domain_path.glob(f"*{ext}"))
            
            # Exclude README files
            files = [f for f in files if not f.name.startswith("README")]
            
            if files:
                stats["by_domain"][domain_name] = len(files)
                stats["total_documents"] += len(files)
    
    return stats


if __name__ == "__main__":
    # Run indexing
    result = index_documents_from_folder()
    
    # Show stats
    stats = get_knowledge_base_stats()
    print("\n📊 Knowledge Base Statistics:")
    print(f"   Total Documents: {stats['total_documents']}")
    for domain, count in stats['by_domain'].items():
        print(f"   - {domain}: {count} files")
