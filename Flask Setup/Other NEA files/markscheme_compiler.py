from urllib.parse import unquote
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import requests
import os

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

question_refs = ['15-S1-Q11', '10-S1-Q12', '07-S2-Q14']
downloader = MarkschemeDownloader(question_refs)
downloader.merge_and_run()
