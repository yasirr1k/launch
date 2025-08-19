import sqlite3
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service



options = webdriver.ChromeOptions()
options.add_argument('--headless')  
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get('https://stepdatabase.maths.org/database/index.html')

topics = []

def clean_topic_name(topic):

    corrections = {
        "Ratinoal points": "Rational points",
        "Curve sketeching": "Curve sketching",
        "Geomtric mean": "Geometric mean",
        "Difference equaetions": "Difference equations",
        'Difference equation': 'Difference equations',
        'Discrete random variable': 'Discrete random variables',
        "Chebyshev'S Inequality": "Chebyshev's Inequality",
        "Work and Power": "Work and power",
        'Coin toss game': 'Coin toss',
        'Coin tosses': 'Coin toss',
        'Coin tossing': 'Coin toss',
        'Differential equation': 'Differential equations',
        'Complex number': 'Complex numbers',
        'Inequality': 'Inequalities',
        'Poisson distribution': 'Poisson distributions',
        'Quadratic equation': 'Quadratic equations',
        'Roots of polynomial': 'Roots of polynomials',
        'Sequence': 'Sequences',
        'Collision': 'Collisions',
    }

    for typo, correction in corrections.items():
        if topic == typo:
            topic = correction

    topic = topic.strip()
    return topic


WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'li')))  
li_tag = driver.find_elements(By.TAG_NAME, 'li')


for i in li_tag:
    try:

        question_id = i.get_attribute('data-question-id')
        if question_id[0] == '8' or question_id[0] == '9':
            continue

        # extract year from question ID
        if len(question_id) == 7:
            year = int(question_id[:4])
        elif len(question_id) == 5:
            year = '20' + (question_id[:2])
            year = int(year)

        # only process questions from 2004 or onwards
        if year >= 2004:

            topic_element = i.find_element(By.XPATH, ".//span[@style='font-weight:normal']/font[@size='3']")
            topic = topic_element.text.strip()

            topic = clean_topic_name(topic)

            if topic not in topics:
                topics.append(topic)

    except:
        print(f"Error getting data for question {i}:")

driver.quit()

topics.sort()  

for topic in topics:
    print(f"Topic: {topic}")

# database
connection = sqlite3.connect("/Users/fathemaislam/Documents/CS NEA/Flask Setup/instance/database.db")
cursor = connection.cursor()


for topic_name in topics:
    # check for duplicates 
    cursor.execute(
        "SELECT 1 FROM topics WHERE topic_name = ?",
        (topic_name,))
    
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO topics (topic_name) VALUES (?)",
            (topic_name,))
        
connection.commit()
connection.close()


