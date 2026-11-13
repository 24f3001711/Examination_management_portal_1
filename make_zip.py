import os
import zipfile

def package_project(zip_filename="projectname_2XfX00XXXX.zip", root_folder_name="Project_Root_Folder"):
    # Folders and file extensions to exclude (matching your .gitignore)
    exclude_dirs = {
        ".venv", "venv", "env", "ENV", ".venv312",
        "__pycache__", ".git", ".vscode", ".idea",
        "instance", ".ipynb_checkpoints"
    }
    exclude_exts = {".pyc", ".pyo", ".pyd", ".db", ".log", ".tmp"}

    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for current_root, dirs, files in os.walk("."):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                # Skip excluded file extensions and the output zip itself
                if any(file.endswith(ext) for ext in exclude_exts) or file == zip_filename:
                    continue

                full_path = os.path.join(current_root, file)
                rel_path = os.path.relpath(full_path, ".")
                
                # Place everything inside the top-level Project Root Folder
                archive_path = os.path.join(root_folder_name, rel_path)
                zipf.write(full_path, archive_path)
                print(f"Added: {archive_path}")

    print(f"\nSuccessfully created {zip_filename}!")

if __name__ == "__main__":
    # Replace with your actual project name and roll/ID number
    package_project(
        zip_filename="Examination_Management_Portal_1_24f3001711.zip",
        root_folder_name="Examination_Management_Portal_1"
    )