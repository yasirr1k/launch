import requests
import re
import sqlite3  


def store(question_ref, question_content):
    connect = sqlite3.connect("/Users/fathemaislam/Documents/CS NEA/Flask Setup/instance/database.db")
    cursor = connect.cursor()
    
    cursor.execute('''
    UPDATE questions
    SET latex = ?
    WHERE question_ref = ?
    ''', (question_content, question_ref))
    
    connect.commit()
    connect.close()


def scrape_latex(year, step):
    url = f"https://stepdatabase.maths.org/database/db/{year}/{year}-S{step}.tex"
    response = requests.get(url)
    return response.text


for year in range(4, 19):  
    if year < 10:
        year = f"0{year}"
    for step in range(1, 4): 
        latex_text = scrape_latex(year, step)
        
  
        if int(year) < 8:
            num_questions = 14
            thirteen = False
        else:
            num_questions = 13
            thirteen = True


        #scraping logic 

        for question_number in range(1, num_questions + 1):

            question_content = ''

            pattern = f"%%Q{question_number}"
            start_idx = latex_text.find(pattern)
            if start_idx == -1:           #accounting for latex inconsistencies
                pattern = f"%% Q{question_number}"
                start_idx = latex_text.find(pattern)
                if start_idx == -1:
                    pattern = f"%%  Q{question_number}"
                    start_idx = latex_text.find(pattern)
                    if start_idx == -1:
                        question_content = None  # Question not found
            

        #deal with reaching end of latex

            if thirteen and question_number == 13:  
                end_idx = len(latex_text)
            elif not thirteen and question_number == 14:
                end_idx = len(latex_text)
            else:
                next_pattern = f"%%Q{question_number + 1}"  
                end_idx = latex_text.find(next_pattern) 
                if end_idx == -1:                 #accounting for latex inconsistencies
                    next_pattern = f"%%% Q{question_number + 1}"
                    end_idx = latex_text.find(next_pattern) 
                    if end_idx == -1:
                        next_pattern = f"%%%  Q{question_number + 1}"
                        end_idx = latex_text.find(next_pattern)
                        if end_idx == -1: 
                            question_content = None
            
            if question_content is None:
                continue 

            question_content = latex_text[start_idx:end_idx].strip()
            
            if question_number == 13 and thirteen:
                question_content = question_content.replace('\end{document}', '')
            elif question_number == 14 and not thirteen:
                question_content = question_content.replace('\end{document}', '')

            #removing unwanted content
            question_content = question_content.replace('\newpage', '')  
            question_content = re.sub(r'\\newpage', '', question_content) 
            question_content = question_content.replace('\section*{Section B: \ \ \ Mechanics}', '')  
            question_content = question_content.replace('\section*{Section C: \ \ \ Probability and Statistics}', '')  


            if question_content:
                question_ref = f"{year}-S{step}-Q{question_number}"
                store(question_ref, question_content)

print("Scraping and updating process complete!")


def clean_latex(latex_content):

    end_idx = latex_content.find('\\end{question}')
    
    if end_idx != -1:

        content_before_end = latex_content[:end_idx + len('\\end{question}')]

        cleaned_content = content_before_end + ('\n')
        return cleaned_content
    
    return latex_content

connect = sqlite3.connect("/Users/fathemaislam/Documents/CS NEA/Flask Setup/instance/database.db")
cursor = connect.cursor()


cursor.execute("SELECT question_ref, latex FROM questions")
rows = cursor.fetchall()


for row in rows:
    question_ref = row[0]
    latex_content = row[1]
    
    if latex_content:

        cleaned_content = clean_latex(latex_content)
        
        cursor.execute('''
        UPDATE questions
        SET latex = ?
        WHERE question_ref = ?
        ''', (cleaned_content, question_ref))


connect.commit()
connect.close()


