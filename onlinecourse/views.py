from django.shortcuts import render
from django.utils.html import format_html
import os
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
import pandas as pd
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# An example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
   submitted_anwsers = []
   for key in request.POST:
       if key.startswith('choice'):
           value = request.POST[key]
           choice_id = int(value)
           submitted_anwsers.append(choice_id)
   return submitted_anwsers



def read_excel_and_render_html(request):
    # Caminho para o arquivo Excel no servidor
    excel_file_path = 'static/onlinecourse/dados_fundos_indices_sharpe.xlsx'

    # Lendo o arquivo Excel usando Pandas
    df = pd.read_excel(excel_file_path)
    # Convertendo a segunda coluna do DataFrame em hiperlinks
    servidor_fundos = "https://maisretorno.com/fundo/"
    df['Link'] = df['Link'].apply(lambda x: format_html('<a href="{}">{}</a>', servidor_fundos+x, x))
    df = df[['Fundo', 'Link', 'sharpe_12M', 'sharpe_24M', 'sharpe24M', 'sharpe_48M', 'sharpe_60', 'sharpe_total']]
    
    novos_nomes_colunas = {
        'sharpe_12M':'12 meses', 
        'sharpe_24M':'24 meses', 
        'sharpe24M':'36 meses', 
        'sharpe_48M':'48 meses', 
        'sharpe_60':'60 meses',
        'sharpe_total':'Total'}
    df.rename(columns=novos_nomes_colunas, inplace=True)
    #df = df.sort_values(by='Total', ascending=False)
    df = df.replace(-9999, '-')
    
    # Convertendo o DataFrame Pandas para HTML
    html_table = df.to_html(classes="table table-striped table-bordered", index=False, escape=False)

    # Renderizando o template com a tabela HTML
    return render(request, 'onlinecourse/excel_table.html', {'html_table': html_table})
