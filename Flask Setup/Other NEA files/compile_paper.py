import sqlite3
from pathlib import Path
import subprocess
import os

def fetch_latex_from_db(question_ref):
    db_path = '/Users/fathemaislam/Documents/CS NEA/Flask Setup/instance/database.db'  
    connect = sqlite3.connect(db_path)
    cursor = connect.cursor()

    cursor.execute("SELECT latex FROM questions WHERE question_ref = ?", (question_ref,))
    result = cursor.fetchone()
    connect.close()

    if result: 
        return result[0]
    else:
        print(f"No latex content found for question_ref: {question_ref}.")
        return None

def make_pdf(file_name, question_references):
    save_path = Path.cwd()
    complete_name = os.path.join(save_path, file_name)

    with open(complete_name, "w") as file:
        file.write(r"\documentclass{article}")
        file.write(r"\usepackage{amsmath, amssymb}")
        file.write(r"\usepackage{graphicx}")
        file.write(r"\usepackage{enumitem}")
        file.write(r"\usepackage{pst-plot}")
        file.write(r"\usepackage{pstricks}")
        file.write(r"\newenvironment{question}{\begin{quote}\itshape}{\end{quote}}")
        file.write(r"\newenvironment{questionparts}{\begin{enumerate}[label=(\alph*)]}{\end{enumerate}}")
        
        # Title page
        file.write(r"\begin{document}")
        file.write(r"\begin{titlepage}")
        file.write(r"\centering")
        file.write(r"\Huge \textbf{STEP Practice Paper}\\[1.5cm]")
        file.write(r"\large You are recommended to spend 20 minutes per question.\\[0.5cm]")
        file.write(r"Each question is worth 20 marks.\\[0.5cm]")
        total_time = len(question_references) * 30
        file.write(rf"You have a total of {total_time} minutes for this paper.\\[0.5cm]")
        file.write(r"After you are done, ensure you mark this paper with the markscheme provided.\\[0.5cm]")
        file.write(r"Input your scores for each question in the 'Enter Scores for Completed Papers'\\")
        file.write(r"in your dashboard.\\[0.5cm]")
        file.write(r"\textbf{Good luck!}")
        file.write(r"\end{titlepage}")
        
        # Add questions with numbering
        question_number = 1
        for question_ref in question_references:
            latex_content = fetch_latex_from_db(question_ref)
            if latex_content:
                file.write(f"\\section*{{Question {question_number}}}\n")
                file.write(r"\begin{question}")
                file.write(latex_content)
                file.write(r"\end{question}")
                file.write(r"\vspace{1.5cm}")  # Adds space between questions
                question_number += 1

        file.write(r"\end{document}")

    # Compile the LaTeX file into a PDF
    subprocess.run(['xelatex', '-interaction=nonstopmode', file_name])

    # Clean up temporary files
    files_to_remove = ['.tex', '.aux', '.log', '.out', '.dvi']
    for ext in files_to_remove:
        temp_file = file_name[:-4] + ext
        if os.path.exists(temp_file):
            os.remove(temp_file)

    # Remove the .tex file as well
    if os.path.exists(complete_name):
        os.remove(complete_name)

def main():
    question_references = [   
        '08-S3-Q3',
        '13-S3-Q8',
        '05-S3-Q14',
        '06-S2-Q14',
        '12-S3-Q13'
    ]

    output_pdf_name = 'step_paper.tex'
    make_pdf(output_pdf_name, question_references)

if __name__ == "__main__":
    main()
