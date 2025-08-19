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

WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'li')))  
li_tags = driver.find_elements(By.TAG_NAME, 'li')


connection = sqlite3.connect('/Users/fathemaislam/Documents/CS NEA/Flask Setup/instance/database.db')
cursor = connection.cursor()

for i in li_tags:
    try:
        question_ref = i.find_element(By.TAG_NAME, 'a').text.strip()

        year_part = question_ref.split('-')[0]  

        if year_part == 'Spec':
            continue

        # only years 2004 and onwards
        if int(year_part)<100 and int(year_part)>20:
            continue
        
        if int(year_part) >= 4:

            question_number = int(question_ref.split('-')[-1][1:])
            if 9 <= question_number <= 11:
                cursor.execute("SELECT type_id FROM question_types WHERE type_name = ?", ("Mechanics",))
            elif 12 <= question_number <= 14:
                cursor.execute("SELECT type_id FROM question_types WHERE type_name = ?", ("Statistics",))
            else:
                cursor.execute("SELECT type_id FROM question_types WHERE type_name = ?", ("Pure",))
            
            type_id_result = cursor.fetchone()
            if not type_id_result:
                continue
            type_id = type_id_result[0]

            unclean_topic_name = i.find_element(By.XPATH, ".//span[@style='font-weight:normal']/font[@size='3']").text.strip()
            topic_name = corrections.get(unclean_topic_name, unclean_topic_name)

            cursor.execute("SELECT topic_id FROM topics WHERE topic_name = ?", (topic_name,))
            topic_id_result = cursor.fetchone()
            if not topic_id_result:
                continue
            topic_id = topic_id_result[0]

            # insert the record into questions table
            cursor.execute(
                "INSERT OR IGNORE INTO questions (question_ref, type_id, topic_id, latex) VALUES (?, ?, ?, '')",
                (question_ref, type_id, topic_id)
            )

    except:
        print(f"Error processing <li> tag.")


driver.quit()

connection.commit()
connection.close()


print("Questions table populated successfully.")
