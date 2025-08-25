import argparse
import json
import re
from typing import Dict, List
from openai import OpenAI
from pathlib import Path
import logging

# Configure logger
logging.basicConfig(
    filename='openai_chat_rag_relation_4o.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_system_prompt(file_path: str) -> str:
    """Load system prompt from text file"""
    with open(file_path, 'r') as f:
        return f.read()


def main():
    # Resource tracking variables
    vector_store = None
    file_handles = []
    uploaded_file_ids = []

    try:
        # Parse arguments
        parser = argparse.ArgumentParser(description='API Relationship Finder')
        parser.add_argument('-i', required=True, help='Input API list file')
        parser.add_argument('-o', required=True, help='Output JSON file')
        args = parser.parse_args()

        # Initialize client
        client = OpenAI()

        # Prepare documentation files
        doc_files = [
            Path("documents") / "JavaScript APIs.html",
            Path("documents") / "Doc and Doc.Media APIs.html",
            Path("documents") / "Undoc_APIs_4o.json"
        ]
        all_files = [f.resolve() for f in doc_files] + [Path(args.i).resolve()]

        # Upload files individually and track IDs
        print("[1/6] Uploading files...")
        for file_path in all_files:
            try:
                with open(file_path, "rb") as f:
                    vs_file = client.files.create(
                        file=f,
                        purpose="assistants"
                    )
                    uploaded_file_ids.append(vs_file.id)
                    print(f"Uploaded: {file_path.name} (ID: {vs_file.id})")
            except Exception as e:
                print(f"Error uploading {file_path}: {str(e)}")
                raise

        # Create vector store
        print("[2/6] Creating vector store...")
        vector_store = client.beta.vector_stores.create(
            name="API Docs Vector Store",
            file_ids=uploaded_file_ids
        )

        # Create assistant
        print("[3/6] Creating assistant...")
        system_prompt = load_system_prompt(Path("prompts") / "system_RAG_relation_infer.txt")
        assistant = client.beta.assistants.create(
            name="API Relationship Analyzer",
            instructions=system_prompt,
            model="gpt-4o",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
        )

        # Process APIs
        print("[4/6] Processing APIs...")
        with open(args.i, 'r') as f:
            apis = [line.strip() for line in f]

        results = {}
        for api in apis:
            try:
                # Create chat thread
                thread = client.beta.threads.create(messages=[{
                    "role": "user",
                    "content": f"""For {api}, list related APIs in JSON array format: ["object.api"]"""
                }])

                logging.info(f"[*] Infer relation for {api}")
                print(f"[*] Infer relation for {api}")

                # Execute analysis
                run = client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=assistant.id
                )

                # Monitor run status
                while run.status not in ["completed", "failed", "cancelled"]:
                    run = client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )

                # Handle response
                if run.status == "completed":
                    messages = client.beta.threads.messages.list(thread.id)
                    response = messages.data[0].content[0].text.value
                    logging.info("Response from LLM")
                    logging.info(response)
                    if match := re.search(r'\[.*\]', response, re.DOTALL):
                        results[api] = json.loads(match.group())
                    else:
                        results[api] = []
                else:
                    results[api] = []
                    logging.error(f"Analysis failed for {api}")
                    print(f"Analysis failed for {api}")

            except Exception as e:
                print(f"Error processing {api}: {str(e)}")
                results[api] = []

        # Save results
        print("[5/6] Saving results...")
        with open(args.o, 'w') as f:
            json.dump(results, f, indent=2)

    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        # Cleanup resources
        print("[6/6] Cleaning up resources...")
        try:
            # Delete uploaded files
            if uploaded_file_ids:
                print("Deleting vector store files...")
                for file_id in uploaded_file_ids:
                    try:
                        client.files.delete(file_id=file_id)
                    except Exception as e:
                        print(f"Error deleting file {file_id}: {str(e)}")

            # Delete vector store
            if vector_store:
                print("Deleting vector store...")
                client.beta.vector_stores.delete(vector_store.id)

            # Close file handles
            for fh in file_handles:
                try:
                    fh.close()
                except:
                    pass

        except Exception as cleanup_error:
            print(f"Cleanup error: {str(cleanup_error)}")

if __name__ == "__main__":
    main()