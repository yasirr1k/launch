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


def make_pdf(file_name, latex_content):
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
        file.write(r"\begin{document}")
        

        file.write(latex_content)


        file.write(r"\end{document}")


    filename_without_extension = file_name[:-4]
    pdf_file_name = filename_without_extension + '.pdf'

    # compile the latex file into a PDF 
    subprocess.run(['xelatex', '-interaction=nonstopmode', file_name])


    subprocess.run(['open', pdf_file_name])
  
 

    files_to_remove = ['.tex', '.aux', '.log', '.out', '.dvi']
    for i in files_to_remove:
        temp_file = file_name[:-4] + i
        if os.path.exists(temp_file):
            os.remove(temp_file)


    print('Paper generated successfully')


def main():
    question_ref = '10-S2-Q9'

    latex_content = fetch_latex_from_db(question_ref)

    output_pdf_name = 'output_question.tex' 
    make_pdf(output_pdf_name, latex_content)


if __name__ == "__main__":
    main()
