from flask import Flask, render_template, url_for, redirect, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
import os
from flask import send_file
import subprocess
from pathlib import Path
import sqlite3
import requests
import time
import io
import sqlite3
from urllib.parse import unquote
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas



app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db_path = os.path.join(os.path.dirname(__file__), "database.db")db = SQLAlchemy()
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'yasir'
db.init_app(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#database
class User(db.Model, UserMixin): 
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

    def get_id(self):
        return str(self.user_id)


class question_types(db.Model):
    __tablename__ = 'question_types'
    type_id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(20), nullable=False, unique=True)

class Topics(db.Model):  
    __tablename__ = 'topics'
    topic_id = db.Column(db.Integer, primary_key=True)
    topic_name = db.Column(db.String(100), nullable=False)
    __table_args__ = (db.UniqueConstraint('topic_name', name='unique_topic_type'),)

class Questions(db.Model):
    __tablename__ = 'questions'
    question_ref = db.Column(db.String(20), primary_key=True)  
    type_id = db.Column(db.Integer, db.ForeignKey('question_types.type_id'), nullable=False)  
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.topic_id'), nullable=False)     
    latex = db.Column(db.Text, nullable=False)


class PaperScores(db.Model):
    __tablename__ = 'paper_scores'

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    paper_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    paper_name = db.Column(db.String(100), nullable=False, unique=False)
    paper_score = db.Column(db.Integer, nullable=True)

    user = db.relationship('User', back_populates='paper_scores')

# add the relationship to User model
'''
allows things like user = User.query.get(1)
paper_scores = user.paper_scores
User.paper_scores = db.relationship('PaperScores', back_populates='user')
'''

User.paper_scores = db.relationship('PaperScores', back_populates='user')


class QuestionScores(db.Model):
    __tablename__ = 'question_scores'

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper_scores.paper_id'), primary_key=True)
    question_ref = db.Column(db.String(20), db.ForeignKey('questions.question_ref'), primary_key=True)
    question_number = db.Column(db.Integer, nullable=True)
    question_score = db.Column(db.Integer, nullable=True)
    usedIn_intelligen = db.Column(db.Boolean, nullable=False)

    #  relationships with other models
    user = db.relationship('User', back_populates='question_scores')
    question = db.relationship('Questions', back_populates='question_scores')


    # ensures the combination of user_id, paper_name, and question_ref is unique
    __table_args__ = (
        db.UniqueConstraint('user_id', 'paper_id', 'question_ref', name='unique_user_paper_question'),
    )

User.question_scores = db.relationship('QuestionScores', back_populates='user')
Questions.question_scores = db.relationship('QuestionScores', back_populates='question')


class newUserRegister(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError('The username already exists. Please choose a different one.')

class loginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')



# Routes


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = loginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = newUserRegister()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)  #hash using bcrypt import
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account successfully created !', 'success')  
        return redirect(url_for('login'))

    return render_template('register.html', form=form)



@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
def home():
    return render_template('home.html')
    
    
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/generate_custom_paper', methods=['GET', 'POST'])
@login_required
def generate_custom_paper():
    selected_topics = request.form.getlist('selected_topics')  
    paper_name = request.form.get('paper_name', '')  # paper name from user form
    

    # load all topics 
    topics = Topics.query.all()

    topics_data = []
    for topic in topics:
        checked = str(topic.topic_id) in selected_topics  # check if the topic is selected
        topics_data.append({
            'topic_id': topic.topic_id,
            'topic_name': topic.topic_name,
            'checked': checked
        })

    # save paper_name and selected_topics to session or pass directly to the next page
    return render_template('generate_custom_paper.html', 
                           topics=topics_data, 
                           paper_name=paper_name, 
                           selected_topics=selected_topics)


# flask route to view question PDF
@app.route('/view_question/<question_ref>', methods=['GET'])
@login_required
def view_question(question_ref):
    latex_content = fetch_latex_from_db(question_ref)
    if latex_content:
        return view_qs_pdf(question_ref, latex_content)
  
    else:
        flash('Question not found or invalid reference.', 'danger')
        return redirect(url_for('dashboard'))
    


@app.route('/serve_pdf/<pdf_filename>')
@login_required
def serve_pdf(pdf_filename,markscheme = False):
    # build the full path 
    pdf_file_path = os.path.join(Path.cwd(), pdf_filename)
    
    # serve the PDF to the user and open it in a new tab
    response = send_file(pdf_file_path, as_attachment=False, mimetype='application/pdf')

    # header tells the browser to open the PDF inline in a new tab 
    response.headers["Content-Disposition"] = "inline; filename=" + pdf_filename

    return response



@app.route('/generate_random_paper', methods=['GET', 'POST'])
@login_required
def generate_random_paper():
    user_id = current_user.get_id()  


    # step 1: get random question references
    question_references = get_random_questions()
    

    # step 2: generate the random paper name
    paper_name = get_next_random_paper_name(user_id)
    temp_paper_name = paper_name


    if not paper_name.endswith('.tex'):
        temp_paper_name += '.tex'  # ensure the paper name ends with '.tex' for latex compilation

    # generate the PDF 
    pdf_file_path = make_paper(temp_paper_name, question_references, 'random')

    # generate the filename for the paper's PDF 
    pdf_filename = os.path.basename(pdf_file_path)


    # step 4: generate the mark scheme PDF
    markscheme_downloader = MarkschemeDownloader(question_references)
    markscheme_file = markscheme_downloader.merge_and_run()

    # step 5: add the paper to the database
    add_paper_to_db(user_id, paper_name,question_references)

    # step 6: redirect to open PDF for paper to be served

    return render_template('open_pdf.html', 
                            pdf_filename=pdf_filename,
                            markscheme_filename=os.path.basename(markscheme_file))



def get_random_questions():

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # query to fetch random questions by category
    query = """
        SELECT question_ref FROM questions WHERE type_id = ? ORDER BY RANDOM() LIMIT ?
    """
    cursor.execute(query, ('1', 8))  # 8 Pure questions
    pure_questions = [row[0] for row in cursor.fetchall()]

    cursor.execute(query, ('2', 3))  # 3 Mechanics questions
    mechanics_questions = [row[0] for row in cursor.fetchall()]

    cursor.execute(query, ('3', 2))  # 2 Statistics questions
    stats_questions = [row[0] for row in cursor.fetchall()]

    connection.close()

    # combine all questions
    return pure_questions + mechanics_questions + stats_questions


def get_next_random_paper_name(user_id):

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Check for existing papers and find the next available number
    cursor.execute("""
        SELECT paper_name FROM paper_scores WHERE user_id = ?
    """, (user_id,))
    existing_papers = [row[0] for row in cursor.fetchall()]

    connection.close()

    # Determine the next increment
    i = 1
    while f"random_paper{i}" in existing_papers:
        i += 1
    return f"random_paper{i}"



def make_paper(file_name, question_references, type):
    save_path = Path.cwd()    

    complete_name = os.path.join(save_path, file_name)

    with open(complete_name, "w") as file:

        #latex environment set up

        file.write(r"\documentclass{article}")
        file.write(r"\usepackage{amsmath, amssymb}")
        file.write(r"\usepackage{graphicx}")
        file.write(r"\usepackage{enumitem}")
        file.write(r"\usepackage{pst-plot}")
        file.write(r"\usepackage{pstricks}")
        file.write(r"\newenvironment{question}{\begin{quote}\itshape}{\end{quote}}")
        file.write(r"\newenvironment{questionparts}{\begin{enumerate}[label=(\alph*)]}{\end{enumerate}}")
        
        # title page
        file.write(r"\begin{document}")
        file.write(r"\begin{titlepage}")
        file.write(r"\centering")


        if type == 'random':
            file.write(r"\Huge \textbf{STEP Gen Random Paper}\\[1.5cm]")
        elif type =='intelligen':
            file.write(r"\Huge \textbf{STEP Gen Intelligen Paper}\\[1.5cm]")
        elif type == 'custom':
            file.write(r"\Huge \textbf{STEP Gen Practice Paper}\\[1.5cm]")


        file.write(r"\large You are recommended to spend 20 minutes per question.\\[0.5cm]")
        file.write(r"Each question is worth 20 marks.\\[0.5cm]")
        file.write(r"Questions are referenced in the form 'year-STEPnumber-questionnumber' for your convenience\\[0.5cm]")

        if type == 'random' or type == 'intelligen':
            file.write(r"Answer at least six questions, as expected in the real exam.\\[0.5cm]")

        file.write(r"\large Calculators are NOT allowed.\\[0.5cm]")

        if type == 'random' or type == 'intelligen':
            total_time = 180
        else:
            total_time = len(question_references)*30

            
        file.write(rf"You have a total of {total_time} minutes for this paper.\\[0.5cm]")
        file.write(r"After you are done, ensure you mark this paper with the markscheme provided.\\[0.5cm]")
        file.write(r"Input your scores for each question in the 'Enter Scores for Completed Papers' page\\")
        file.write(r"in your dashboard.\\[0.5cm]")
        file.write(r"\textbf{Good luck!}")
        file.write(r"\end{titlepage}")
        

        if type == 'random' or type == 'intelligen':

            # add Pure section heading before the first question
            file.write(r"\newpage")  # start a new page for sections
            file.write(r"\section*{Section A: Pure}")
            file.write(r"\vspace{0.5cm}")  # add space after the section title
            
            # add Pure questions (first 8 questions)
            question_number = 1
            for i in range(8):
                question_ref = question_references[i]
                latex_content = fetch_latex_from_db(question_ref)
                if latex_content:
                    file.write(f"\\section*{{Question {question_number} ({question_ref})}}\n")
                    file.write(r"\begin{question}")
                    file.write(latex_content)
                    file.write(r"\end{question}")
                    file.write(r"\vspace{1.5cm}")  
                    question_number += 1
            
            # add Mechanics  heading after the 8th question
            file.write(r"\newpage")  
            file.write(r"\section*{Section B: Mechanics}")
            file.write(r"\vspace{0.5cm}")  
            
            # add Mechanics questions 
            for i in range(8, 11):
                question_ref = question_references[i]
                latex_content = fetch_latex_from_db(question_ref)
                if latex_content:
                    file.write(f"\\section*{{Question {question_number} ({question_ref})}}\n")
                    file.write(r"\begin{question}")
                    file.write(latex_content)
                    file.write(r"\end{question}")
                    file.write(r"\vspace{1.5cm}") 
                    question_number += 1
            
            # add Statistics section heading
            file.write(r"\newpage")  
            file.write(r"\section*{Section C: Statistics}")
            file.write(r"\vspace{0.5cm}") 
            
            # Add Statistics questions
            for i in range(11, len(question_references)):
                question_ref = question_references[i]
                latex_content = fetch_latex_from_db(question_ref)
                if latex_content:
                    file.write(f"\\section*{{Question {question_number} ({question_ref})}}\n")
                    file.write(r"\begin{question}")
                    file.write(latex_content)
                    file.write(r"\end{question}")
                    file.write(r"\vspace{1.5cm}")  
                    question_number += 1

            file.write(r"\end{document}")
        
        
        else:
         # Add questions with numbering
            question_number = 1
            for question_ref in question_references:
                latex_content = fetch_latex_from_db(question_ref)
                if latex_content:
                    file.write(f"\\section*{{Question {question_number} ({question_ref})}}\n")
                    file.write(r"\begin{question}")
                    file.write(latex_content)
                    file.write(r"\end{question}")
                    file.write(r"\vspace{1.5cm}") 
                    question_number += 1

            file.write(r"\end{document}")           

    # Compiling the latex
    subprocess.run(['xelatex', '-interaction=nonstopmode', complete_name])

    files_to_remove = ['.tex', '.aux', '.log', '.out', '.dvi']
    for ext in files_to_remove:
        temp_file = complete_name[:-4] + ext
        if os.path.exists(temp_file):
            os.remove(temp_file)

    # Return the pdf file path
    pdf_file_path = complete_name[:-4] + '.pdf'
    return pdf_file_path





@app.route('/enter_scores', methods=['GET', 'POST'])
@login_required
def enter_scores():
    user_id = current_user.get_id()

    # fetch all papers with a score of -1 for the current user

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT paper_id, paper_name FROM paper_scores 
        WHERE user_id = ? AND paper_score = -1
    """, (user_id,))
    papers = cursor.fetchall()  # list of (paper_id, paper_name)

    connection.close()

    if request.method == 'POST':
        paper_id = request.form.get('paper_id')
        if paper_id:
            return redirect(url_for('mark_paper', paper_id=paper_id))

    return render_template('enter_scores.html', papers=papers)


@app.route('/mark_paper/<int:paper_id>', methods=['GET', 'POST'])
@login_required
def mark_paper(paper_id):
    user_id = current_user.get_id()


    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # fetch questions for this paper, ordered by question_number
    cursor.execute("""
        SELECT question_number, question_ref FROM question_scores 
        WHERE user_id = ? AND paper_id = ?
        ORDER BY question_number ASC
    """, (user_id, paper_id))
    questions = cursor.fetchall()  # list of (question_number, question_ref) in order

    if request.method == 'POST':
        total_score = 0
        scores = {}

        for question_number, question_ref in questions:
            score = request.form.get(f"score_{question_number}")
            try:
                score = float(score)
                if score < 0 or score > 20:
                    flash(f"Invalid score for Question {question_number}. Must be between 0 and 20.", "danger")
                    return redirect(url_for('mark_paper', paper_id=paper_id))
                scores[question_ref] = score
                total_score += score
            except ValueError:
                flash(f"Invalid input for Question {question_number}. Please enter a number.", "danger")
                return redirect(url_for('mark_paper', paper_id=paper_id))

        # update scores in the database
        for question_ref, score in scores.items():
            cursor.execute("""
                UPDATE question_scores 
                SET question_score = ? 
                WHERE user_id = ? AND paper_id = ? AND question_ref = ?
            """, (score, user_id, paper_id, question_ref))

        # update total paper score
        cursor.execute("""
            UPDATE paper_scores 
            SET paper_score = ? 
            WHERE paper_id = ?
        """, (total_score, paper_id))

        connection.commit()
        connection.close()

        flash("Scores updated successfully!", "success")
        time.sleep(1)

        return redirect(url_for('dashboard'))

    connection.close()
    return render_template('mark_paper.html', paper_id=paper_id, questions=questions)




@app.route('/generate_intelligen_paper', methods=['GET', 'POST'])
@login_required
def generate_intelligen_paper():
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    user_id = current_user.get_id()

# pure questions
    cursor.execute("""
        SELECT question_scores.question_ref, question_scores.question_score, questions.topic_id
        FROM question_scores
        JOIN questions ON question_scores.question_ref = questions.question_ref
        WHERE question_scores.usedIn_intelligen = 0 
          AND question_scores.user_id = ? 
          AND question_scores.question_score > 0 
          AND question_scores.question_score < 12
          AND questions.type_id = 1
    """, (user_id,))
    pure_questions = cursor.fetchall()  # (question_ref, score, topic_id)
    print(pure_questions)
    
    # sort by score (ascending)
    pure_questions.sort(key=lambda x: x[1])  # priority queue

    selected_pure_questions = []
    used_topics = set()


    while len(selected_pure_questions) < 8 and len(pure_questions)>0:
        # pop the question with the lowest score from queue
        question_ref, score, topic_id = pure_questions.pop(0)

        # add to selected list & mark as used
        selected_pure_questions.append(question_ref)
        used_topics.add(topic_id)
        cursor.execute("UPDATE question_scores SET usedIn_intelligen = 1 WHERE question_ref = ? AND user_id=?", (question_ref,user_id))

        # find more questions with the same topic_id
        cursor.execute("""
            SELECT question_ref FROM questions
            WHERE topic_id = ? 
              AND question_ref NOT IN ({})
        """.format(",".join("?" * len(selected_pure_questions))), (topic_id, *selected_pure_questions))
        topic_questions = [i[0] for i in cursor.fetchall()]

        for i in topic_questions:
            if len(selected_pure_questions) < 8:
                selected_pure_questions.append(i)

    # If still less than 8, add random pure questions
    while len(selected_pure_questions) < 8:
        random_question = get_random_questions()[0]
        selected_pure_questions.append(random_question)

    # mechanics questions
    cursor.execute("""
        SELECT question_scores.question_ref, question_scores.question_score, questions.topic_id
        FROM question_scores
        JOIN questions ON question_scores.question_ref = questions.question_ref
        WHERE question_scores.usedIn_intelligen = 0 
          AND question_scores.user_id = ? 
          AND question_scores.question_score > 0 
          AND question_scores.question_score < 12
          AND questions.type_id = 2
    """, (user_id,))
    mech_questions = cursor.fetchall()
    mech_questions.sort(key=lambda x: x[1])

    selected_mech_questions = []
    used_topics = set()

    while len(selected_mech_questions) < 3 and mech_questions:
        question_ref, score, topic_id = mech_questions.pop(0)
        selected_mech_questions.append(question_ref)
        used_topics.add(topic_id)
        cursor.execute("UPDATE question_scores SET usedIn_intelligen = 1 WHERE question_ref = ? AND user_id=?", (question_ref,user_id))

        cursor.execute("""
            SELECT question_ref FROM questions
            WHERE topic_id = ? 
              AND question_ref NOT IN ({})
        """.format(",".join("?" * len(selected_mech_questions))), (topic_id, *selected_mech_questions))
        topic_questions = [i[0] for i in cursor.fetchall()]

        for i in topic_questions:
            if len(selected_mech_questions) < 3:
                selected_mech_questions.append(i)

    while len(selected_mech_questions) < 3:
        random_question = get_random_questions()[10]
        selected_mech_questions.append(random_question)

    # stats questions
    cursor.execute("""
        SELECT question_scores.question_ref, question_scores.question_score, questions.topic_id
        FROM question_scores
        JOIN questions ON question_scores.question_ref = questions.question_ref
        WHERE question_scores.usedIn_intelligen = 0 
          AND question_scores.user_id = ? 
          AND question_scores.question_score > 0 
          AND question_scores.question_score < 12
          AND questions.type_id = 3
    """, (user_id,))
    stats_questions = cursor.fetchall()
    stats_questions.sort(key=lambda x: x[1])

    selected_stats_questions = []
    used_topics = set()

    while len(selected_stats_questions) < 2 and stats_questions:
        question_ref, score, topic_id = stats_questions.pop(0)
        selected_stats_questions.append(question_ref)
        used_topics.add(topic_id)
        cursor.execute("UPDATE question_scores SET usedIn_intelligen = 1 WHERE question_ref = ? AND user_id=?", (question_ref,user_id))

        cursor.execute("""
            SELECT question_ref FROM questions
            WHERE topic_id = ? 
              AND question_ref NOT IN ({})
        """.format(",".join("?" * len(selected_stats_questions))), (topic_id, *selected_stats_questions))
        topic_questions = [i[0] for i in cursor.fetchall()]

        for i in topic_questions:
            if len(selected_stats_questions) < 2:
                selected_stats_questions.append(i)

    while len(selected_stats_questions) < 2:
        random_question = get_random_questions()[12]
        selected_stats_questions.append(random_question)


    selected_questions = selected_pure_questions + selected_mech_questions + selected_stats_questions

    # ensure unique paper name
    num = 1
    paper_name = "intelligen_paper_1"
    
    while True:
        cursor.execute("SELECT COUNT(*) FROM paper_scores WHERE paper_name = ?", (paper_name,))
        if cursor.fetchone()[0] == 0:
            break
        paper_name = f'intelligen_paper_{num+1}'
        num+=1

    #  mark all selected questions as used
    for question_ref in selected_questions:
        cursor.execute("UPDATE question_scores SET usedIn_intelligen = 1 WHERE question_ref = ? AND user_id=?", (question_ref,user_id))

    connection.commit()

# generate markscheme for the paper
    temp_paper_name = paper_name if paper_name.endswith('.tex') else f"{paper_name}.tex"
    pdf_file_path = make_paper(temp_paper_name, selected_questions, 'intelligen')
    pdf_filename = os.path.basename(pdf_file_path)

    try:
        markscheme_downloader = MarkschemeDownloader(selected_questions)
        markscheme_path = "markscheme.pdf"
        markscheme_result = markscheme_downloader.merge_and_run(output_file=markscheme_path)

        if not markscheme_result:
            flash("Mark scheme generation failed.", "danger")
            return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"An error occurred during mark scheme generation: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

    add_paper_to_db(user_id, paper_name, selected_questions)


    return render_template(
        'open_pdf.html',
        pdf_filename=pdf_filename,
        markscheme_filename=os.path.basename(markscheme_path)
    )



@app.route('/view_previous_papers', methods=['GET', 'POST'])
@login_required
def view_previous_papers():
    user_id = current_user.get_id()

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # get all papers for the user
    cursor.execute("""
        SELECT paper_id, paper_name, paper_score 
        FROM paper_scores 
        WHERE user_id = ?
        ORDER BY paper_id DESC
    """, (user_id,))
    papers = cursor.fetchall()  # list of (paper_id, paper_name, paper_score)

    all_papers = []

    for paper_id, paper_name, paper_score in papers:
        # get all questions for this paper
        cursor.execute("""
              SELECT qs.question_ref, qs.question_score, q.topic_id, q.type_id
            FROM question_scores qs
            JOIN questions q ON qs.question_ref = q.question_ref
            WHERE qs.user_id = ? AND qs.paper_id = ?
            ORDER BY qs.question_number ASC
        """, (user_id, paper_id))
        questions = cursor.fetchall()  

        # get topic names & question type names
        formatted_questions = []
        for question_ref, question_score, topic_id, type_id in questions:
            cursor.execute("SELECT topic_name FROM topics WHERE topic_id = ?", (topic_id,))
            topic_name = cursor.fetchone()[0]

            cursor.execute("SELECT type_name FROM question_types WHERE type_id = ?", (type_id,))
            type_name = cursor.fetchone()[0]

            formatted_questions.append({
                'question_ref': question_ref,
                'topic': topic_name,
                'type': type_name,
                'score': "Not marked yet" if question_score == -1 else question_score
            })

        all_papers.append({
            'paper_id': paper_id,
            'paper_name': paper_name,
            'paper_score': "Not marked yet" if paper_score == -1 else paper_score,
            'questions': formatted_questions
        })

    # handle "View Paper & Markscheme" request
    if request.method == 'POST' and 'view_paper_markscheme' in request.form:
        paper_id = int(request.form.get('paper_id'))
        selected_paper = next((p for p in all_papers if p['paper_id'] == paper_id), None)

        if selected_paper:
            selected_questions = [q['question_ref'] for q in selected_paper['questions']]
            paper_name = selected_paper['paper_name']
            random = False
            intelligen = False
            if paper_name.startswith('random_paper'):
                random =True
            elif paper_name.startswith('intelligen_paper'):
                intelligen = True

            if not paper_name.endswith('.tex'):
                paper_name += '.tex'

            # generate paper
            if random == True:
                pdf_file_path = make_paper(paper_name, selected_questions,'random')
            elif intelligen == True:
                pdf_file_path = make_paper(paper_name,selected_questions, 'intelligen')
            else:
                pdf_file_path = make_paper(paper_name,selected_questions, 'custom')

            pdf_filename = os.path.basename(pdf_file_path)

            # markscheme
            try:
                markscheme_downloader = MarkschemeDownloader(selected_questions)
                markscheme_path = "markscheme.pdf"
                markscheme_result = markscheme_downloader.merge_and_run(output_file=markscheme_path)

                if not markscheme_result:
                    flash("Mark scheme generation failed.", "danger")
                    return redirect(url_for('view_previous_papers'))
            except Exception as e:
                flash(f"An error occurred during mark scheme generation: {str(e)}", "danger")
                return redirect(url_for('view_previous_papers'))

            # Render template with PDF filenames for opening in new tabs
            return render_template('open_pdf.html', 
                                   pdf_filename=pdf_filename,
                                   markscheme_filename=os.path.basename(markscheme_path))

    connection.close()
    return render_template('view_previous_papers.html', papers=all_papers)


@app.route('/forget_paper/<int:paper_id>', methods=['POST'])
@login_required
def forget_paper(paper_id):
    user_id = current_user.get_id()

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    try:
        # delete from question scores first
        cursor.execute("DELETE FROM question_scores WHERE user_id = ? AND paper_id = ?", (user_id, paper_id))

        # now delete the paper itself
        cursor.execute("DELETE FROM paper_scores WHERE user_id = ? AND paper_id = ?", (user_id, paper_id))

        connection.commit()
        flash("Paper deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting paper: {str(e)}", "danger")
    finally:
        connection.close()

    return redirect(url_for('view_previous_papers'))




@app.route('/exam_mode', methods=['GET', 'POST'])
@login_required
def exam_mode():
    user_id = current_user.get_id()  

    # fetch available papers for the user
    db_path = '/Users/fathemaislam/Documents/CS NEA/Flask Setup/instance/database.db'
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute("SELECT paper_id, paper_name FROM paper_scores WHERE user_id = ? AND paper_score=-1", (user_id,))
    papers = cursor.fetchall()  # list of (paper_id, paper_name)
    
    connection.close()

    if request.method == 'POST':
        selected_paper_id = request.form.get('selected_paper')

        if selected_paper_id:
            #  number of questions in this paper
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM question_scores WHERE paper_id = ?", (selected_paper_id,))
            num_questions = cursor.fetchone()[0]

            #  paper name
            cursor.execute("SELECT paper_name FROM paper_scores WHERE paper_id = ?", (selected_paper_id,))
            paper_name = cursor.fetchone()[0]

            connection.close()

            # calculate time allowed (30 mins per question)
            if num_questions == 13:
                time_allowed = 180*60 #for exam papers only it differnet 
            else:
                time_allowed = num_questions * 30 * 60  # Convert minutes to seconds

            return render_template('exam_timer.html', paper_id=selected_paper_id, time_allowed=time_allowed, paper_name=paper_name)

    return render_template('exam_mode.html', papers=papers)



def view_qs_pdf(question_ref, latex_content):
    save_path = Path.cwd()
    file_name = f'{question_ref}.tex'
    complete_name = os.path.join(save_path, file_name)

    # Create the latex file
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

    pdf_file_name = f"{question_ref}.pdf"
    pdf_file_path = os.path.join(save_path, pdf_file_name)

    # compile the latex file into a pdf
    subprocess.run(['xelatex', '-interaction=nonstopmode', complete_name])


    response = send_file(pdf_file_path, as_attachment=False)

    # After the file has been sent, delete the generated pdf and temporary latex files
    if os.path.exists(pdf_file_path):
        os.remove(pdf_file_path)

    # clean up the .tex file and other temporary files
    files_to_remove = ['.tex', '.aux', '.log', '.out', '.dvi']
    for temp_file in files_to_remove:
        temp_file_path = complete_name[:-4] + temp_file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return response




@app.route('/view_questions', methods=['GET', 'POST'])
@login_required
def view_questions():
    if request.method == 'POST':
        selected_topics = request.form.getlist('selected_topics')  # get list of selected topics
        paper_name = request.form.get('paper_name', '')  # paper name from the form

        # prepare questions for selected topics
        questions = {}
        if selected_topics:
            for topic_id in selected_topics:
                topic = Topics.query.get(topic_id)
                topic_questions = Questions.query.filter_by(topic_id=topic.topic_id).all()
                question_data = []
                for question in topic_questions:
                    question_type = question_types.query.get(question.type_id)
                    question_data.append({
                        'question_ref': question.question_ref,
                        'type_name': question_type.type_name,
                        'latex': question.latex  
                    })
                questions[topic.topic_name] = question_data

        return render_template('view_questions.html', 
                               questions=questions, 
                               paper_name=paper_name, 
                               selected_topics=selected_topics)

    return redirect(url_for('generate_custom_paper'))  # redirect to generate_custom_paper if not POST

    


@app.route('/generate_custompaper', methods=['POST'])
@login_required
def generate_custompaper():
    selected_questions = request.form.getlist('selected_questions')  # get list of selected question references
    paper_name = request.form.get('paper_name', 'step_paper')  # default to 'step_paper' if no name provided

    if not is_paper_unique(paper_name,int(current_user.get_id())):
        flash(f"The paper name '{paper_name}' already exists. Please choose a different one.", "error")
        return redirect(url_for('generate_custom_paper'))



    if not selected_questions:
        flash('No questions were selected. Please select topics to generate the paper.', 'danger')
        return redirect(url_for('view_questions'))

    if not paper_name.endswith('.tex'):
        paper_name += '.tex'  # ensure the paper name ends with '.tex'

    # generate the pdf for the paper
    pdf_file_path = make_paper(paper_name, selected_questions, 'custom')

    # filename 
    pdf_filename = os.path.basename(pdf_file_path)

    # mark scheme generation
    try:
        markscheme_downloader = MarkschemeDownloader(selected_questions)
        markscheme_path = "markscheme.pdf"  
        markscheme_result = markscheme_downloader.merge_and_run(output_file=markscheme_path)

# insert paper into database

        if not markscheme_result:
            flash("Mark scheme generation failed.", "danger")
            return redirect(url_for('view_questions'))
    except Exception as e:
        flash(f"An error occurred during mark scheme generation: {str(e)}", "danger")
        return redirect(url_for('view_questions'))


    flash(f"Paper '{pdf_filename}' has been successfully generated!", 'success')
    
    add_paper_to_db(int(current_user.get_id()), paper_name[:-4],selected_questions)

    # open both the paper and the mark scheme in new tabs
    return render_template('open_pdf.html', 
                           pdf_filename=pdf_filename,
                           markscheme_filename=os.path.basename(markscheme_path))



def add_paper_to_db(user_id, paper_name, questions):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Add the paper into the paper_scores table and retrieve the paper_id
    cursor.execute(
        "INSERT OR IGNORE INTO paper_scores (user_id, paper_name, paper_score) VALUES (?, ?, ?)",
        (user_id, paper_name, -1)
    )
    
    # Retrieve the last inserted paper_id
    cursor.execute("SELECT last_insert_rowid()")
    paper_id = cursor.fetchone()[0]

    # Insert the corresponding questions into the question_scores table using paper_id
    for i in range(len(questions)):
        cursor.execute(
            "INSERT INTO question_scores (user_id, paper_id, question_ref,question_number, question_score, usedIn_intelligen) VALUES (?, ?, ?, ?, ?,?)",
            (user_id, paper_id,questions[i], i+1, -1, False)
        )

    connection.commit()
    connection.close()



def fetch_latex_from_db(question_ref):

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








class MarkschemeDownloader:
   def __init__(self, question_refs):
       self.question_refs = question_refs
       self.downloaded_files = []


   def download_pdf(self, url, filename):
       url = unquote(url)
       try:
           response = requests.get(url)
           with open(filename, "wb") as f:
               for i in response.iter_content(chunk_size=1024):
                   f.write(i)
           print(f"Downloaded and saved as {filename}")
           return filename
       except:
           print(f"Error downloading {filename} ")
           return None




   def generate_linkpage(self, year, step, question_num):
       # generate  link for STEP 1 before 2008
       link = f"https://www.physicsandmathstutor.com/pdf-pages/?pdf=https%3A%2F%2Fpmt.physicsandmathstutor.com%2Fdownload%2FAdmissions%2FSTEP%2FSolutions-and-Reports%2F{year}%20Hints%20and%20Answers.pdf"
       filename = f"link_page_{year}_{step}_Q{question_num}.pdf"


       c = canvas.Canvas(filename, pagesize=letter)
       c.drawString(100, 600, f"STEP {step} {year} Question {question_num} Mark Scheme:")
       c.drawString(100, 580, f"The full markscheme is available online for {year}'s STEP{step} paper.")
       c.drawString(100, 560, f"Click the link below and scroll to question {question_num} to access it:")
       
       link_width = c.stringWidth(f"Click here: ACCESS THE MARKSCHEME PACK FOR {year} STEP{step} PAPER")
       c.linkURL(link, (100, 540, 100 + link_width, 550), relative=0)  
       c.drawString(100, 540, f"Click here: -ACCESS THE MARKSCHEME PACK FOR {year} STEP{step} PAPER-")

       c.showPage()
       c.save()


       print(f"Generated link page for {year}-{step}-Q{question_num} at {filename}")
       return filename



   def questionPages(self, pdf_file, question_num, year):
        with pdfplumber.open(pdf_file) as pdf:
            num_pages = len(pdf.pages)
            start_page = 0
            end_page = num_pages

            for i in range(num_pages):
                text = pdf.pages[i].extract_text()
                if text and (f"Question {question_num}" in text or f"Q{question_num}" in text):
                    start_page = i
                    break

            for i in range(start_page, num_pages):
                text = pdf.pages[i].extract_text()
                if text and (f"Question {int(question_num) + 1}" in text or f"Q{int(question_num)+1}" in text):
                    end_page = i
                    break

            if start_page != 0:
                pdf_writer = PdfMerger()
                list_of_questions = [i for i in range(int(question_num)-1,int(question_num)+2)]
                list_of_questions.remove(int(question_num))
                text = pdf.pages[start_page].extract_text()
                extras_found = False

                for i in list_of_questions:
                    if (f"Question {int(question_num)}") in text and (f"Question {i}") in text:
                        # create a temporary PDF with the instruction "In the next page, ignore other"
                        packet = io.BytesIO()
                        c = canvas.Canvas(packet, pagesize=letter)

                        # Add the overlay text at the top of the new page
                        c.setFont("Helvetica", 12)
                        c.drawString(50, 750, f"In the next page, ignore the other Question markschemes. ")
                        if len(question_num)==1:
                            c.drawString(50,730, f'The only relevant markscheme for {year[2:]}-S1-0{question_num} is Question {question_num}.')
                        else:
                            c.drawString(50,730, f'The only relevant markscheme for {year[2:]}-S1-{question_num} is Question {question_num}.')

                        c.save()

                        packet.seek(0)
                        overlay_pdf = PdfReader(packet)

                        overlay_pdf_path = "overlay_page.pdf"
                        with open(overlay_pdf_path, "wb") as overlay_file:
                            overlay_pdf_writer = PdfWriter()
                            overlay_pdf_writer.add_page(overlay_pdf.pages[0])
                            overlay_pdf_writer.write(overlay_file)

                        pdf_writer.append(overlay_pdf_path)
                        pdf_writer.append(pdf_file, pages=(start_page, start_page + 1))

                        os.remove(overlay_pdf_path)
                        extras_found = True
                        break
                    if (f"Q{int(question_num)}") in text and (f"Q{i}") in text:
                        # create a temporary PDF with the instruction ignore other questions"
                        packet = io.BytesIO()
                        c = canvas.Canvas(packet, pagesize=letter)

                        c.setFont("Helvetica", 12)
                        c.drawString(50, 750, f"In the next page, ignore the other Question markschemes. ")
                        if len(question_num)==1:
                            c.drawString(50,730, f'The only relevant markscheme for {year[2:]}-S1-0{question_num} is Question {question_num}.')
                        else:
                            c.drawString(50,730, f'The only relevant markscheme for {year[2:]}-S1-{question_num} is Question {question_num}.')

                        c.save()

                        packet.seek(0)
                        overlay_pdf = PdfReader(packet)

                        overlay_pdf_path = "overlay_page.pdf"
                        with open(overlay_pdf_path, "wb") as overlay_file:
                            overlay_pdf_writer = PdfWriter()
                            overlay_pdf_writer.add_page(overlay_pdf.pages[0])
                            overlay_pdf_writer.write(overlay_file)

                        pdf_writer.append(overlay_pdf_path)
                        pdf_writer.append(pdf_file, pages=(start_page, start_page + 1))

                        os.remove(overlay_pdf_path)
                        extras_found =True
                        break
                if extras_found == False:
                    for j in range(start_page, end_page or num_pages):
                        pdf_writer.append(pdf_file, pages=(j, j + 1))

                output_filename = f"question_{question_num}_{year}_extracted.pdf"
                with open(output_filename, "wb") as output_pdf:
                    pdf_writer.write(output_pdf)

            

                print(f"Extracted question {question_num} year {year} to {output_filename}")
                return output_filename




   def nextstepMarkscheme(self, year, step, question_num):
       url = f"https://nextstepmaths.com/downloads/step-questions-and-solutions/step{step}-{year}-q{question_num}ms.pdf"
       filename = f"step{step}-{year}-q{question_num}ms.pdf"


       try:
           response = requests.get(url)
           with open(filename, "wb") as x:
               x.write(response.content)
           print(f"Downloaded: {filename}")
           return filename
       except:
           print(f'Error fetching {filename}')
           return None




   def allMarkschemes(self):
       for i in self.question_refs:
           year, step, question_num = i.split('-')
           year = '20' + year.strip()
           step = step.strip()[1]
           question_num = question_num.strip()[1:]




           if step == "1" and int(year) < 2008:
               linkpage = self.generate_linkpage(year, step, question_num)
               if linkpage:
                   self.downloaded_files.append(linkpage)
               continue 


           elif step == "1" and int(year) >= 2018:
               url = f'https%3A%2F%2Fpmt.physicsandmathstutor.com%2Fdownload%2FAdmissions%2FSTEP%2FSolutions-and-Reports%2F{year}%20STEP%201%20Solutions.pdf'
           elif step == '3' and int(year) >= 2018:
               url = f'https%3A%2F%2Fpmt.physicsandmathstutor.com%2Fdownload%2FAdmissions%2FSTEP%2FSolutions-and-Reports%2F{year}%20STEP%203%20Solutions.pdf'
           elif step == '1' and int(year)<2018:
               url = f'https%3A%2F%2Fpmt.physicsandmathstutor.com%2Fdownload%2FAdmissions%2FSTEP%2FSolutions-and-Reports%2F{year}%20Solutions.pdf'




           else:
               pdf = self.nextstepMarkscheme(year, step, question_num)
               if pdf:
                   self.downloaded_files.append(pdf)
               continue


           pdf_file = self.download_pdf(url, f"step{step}_marks_{year}.pdf")
           if pdf_file:
               question_pdf = self.questionPages(pdf_file, question_num,year)
               if question_pdf:
                   self.downloaded_files.append(question_pdf)
                   os.remove(f'step{step}_marks_{year}.pdf')




   def merge_and_run(self, output_file=None):
       if output_file is None:
        output_file = os.path.join(os.getcwd(), "markscheme.pdf")

       self.allMarkschemes()


       if self.downloaded_files:
           merger = PdfMerger()


           for pdf in self.downloaded_files:
               merger.append(pdf)


           with open(output_file, "wb") as f:
               merger.write(f)


           print(f"Final merged PDF saved as {output_file}")


           for file in self.downloaded_files:
               os.remove(file)


           return output_file
       else:
           print("No mark schemes downloaded.")
           return None




def is_paper_unique(paper_name, user_id):

    connection = sqlite3.connect(db_path) 
    cursor = connection.cursor()

    query = """
        SELECT paper_name 
        FROM paper_scores 
        WHERE paper_name = ? AND user_id = ?
    """
    cursor.execute(query, (paper_name, user_id))
    existing_paper = cursor.fetchone()

    connection.close()

    # If the query returns None, the paper name is unique for the user
    return existing_paper is None



if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Ensures the database tables are created
    app.run(debug=True)
