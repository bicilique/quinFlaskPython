from app import app
from sqlalchemy import func
from flask import render_template, request, redirect, url_for, session, g, flash
from werkzeug.urls import url_parse
from app.forms import LoginForm, RegistrationForm, QuestionForm
from app.models import User, Questions,City
from app import db
from datetime import datetime, timedelta
import requests
import string
import random




def process_weather_data(weather_data):
    # Memeriksa apakah data cuaca ada
    if weather_data is not None:
        # Mengambil semua data dari respons
        forecast_data = weather_data.get('list', [])
        # Mengelompokkan data berdasarkan tanggal
        grouped_data = {}
        for data in forecast_data:
            dt_txt = data.get('dt_txt', '')
            date = datetime.strptime(dt_txt, '%Y-%m-%d %H:%M:%S').date()
            if date not in grouped_data:
                grouped_data[date] = []
            grouped_data[date].append(data)
        # Ambil 3 data untuk setiap tanggal dengan selisih waktu setiap 6 jam
        selected_data = {}
        for date, data_list in grouped_data.items():
            selected_data[date] = data_list[:8]

        return selected_data
    else:
        return None

def get_weather_data(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid=239c4782fc2cb1529d07d3130fba7438"
    r = requests.get(url).json()
    return r

def get_forecast_data(city):
    api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Ganti dengan kunci API OpenWeatherMap Anda
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&appid=239c4782fc2cb1529d07d3130fba7438"

    # Mengirim HTTP GET request ke OpenWeatherMap API
    response = requests.get(url)

    # Memeriksa apakah request berhasil (status code 200)
    if response.status_code == 200:
        # Mengembalikan data cuaca yang diperoleh dari respons JSON
        return response.json()
    else:
        # Jika request tidak berhasil, mencetak pesan kesalahan
        print(f"Error {response.status_code}: {response.text}")
        return None

def query_city_weather():
    cities = City.query.all()
    if cities == []:
        new_city = City(name="Jakarta")
        db.session.add(new_city)
        db.session.commit()
        print("Telah menambahkan Jakarta")
    weather_data = []
    for city in cities:
        r = get_weather_data(city.name)
        weather = {
            'city' : city.name,
            'temperature' : r['main']['temp'],
            'description' : r['weather'][0]['description'],
            'icon' : r['weather'][0]['icon'],
        }
        weather_data.append(weather)  
    return weather_data

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        user = User.query.filter_by(id=session['user_id']).first()
        g.user = user
        if 'last_question' not in session:
            session['last_question'] = None

# @app.route('/')
@app.route('/', methods=['GET', 'POST'])
def home():
    session['last_question'] = None
    city_name = "Jakarta"
    forecast_data = get_forecast_data(city_name)
    processed_data = None
    table_data = None

    page = int(request.args.get('page', 1))
    per_page = 5

    if forecast_data is not None:
        processed_data = process_weather_data(forecast_data)
        if processed_data is not None:
            total_rows = sum(len(data_list) for data_list in processed_data.values())
            start_index = (page - 1) * per_page
            end_index = min(start_index + per_page, total_rows)

            table_data = []
            for date, data_list in processed_data.items():
                for data in data_list[start_index:end_index]:
                    table_row = {
                        'Date': date.strftime('%Y-%m-%d'),
                        'Time': data['dt_txt'],
                        'Temperature': data['main']['temp'],
                        'Description': data['weather'][0]['description']
                    }
                    table_data.append(table_row)
            table_data = table_data[:14]


    if request.method == 'POST':
        err_msg = ''
        new_city = request.form.get('city')
        new_city = new_city.lower()
        new_city = string.capwords(new_city)
        if new_city:
            existing_city = City.query.filter_by(name=new_city).first()
            
            if not existing_city:
                new_city_data = get_weather_data(new_city)
                if new_city_data['cod'] == 200:
                    new_city_obj = City(name=new_city)
                    db.session.add(new_city_obj)
                    db.session.commit()
                else:
                    err_msg = 'Nama Kota tidak valid!'
            else:
                err_msg = 'Kota sudah ada didalam Database!'
        if err_msg:
            flash(err_msg, 'error')
        else:
            flash('Kota berhasil ditambahkan!', 'success')      

    weather_data = query_city_weather()
    return render_template('index.html', title='Beranda',weather_data=weather_data,table_data=table_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            return redirect(url_for('login'))
        session['user_id'] = user.id
        session['marks'] = user.get_marks()
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)
        return redirect(url_for('home'))
    if g.user:
        return redirect(url_for('home'))
    return render_template('login.html', form=form, title='Login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.password.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['marks'] = 0
        return redirect(url_for('home'))
    if g.user:
        return redirect(url_for('home'))
    return render_template('register.html', title='Register', form=form)



@app.route('/question/<int:id>', methods=['GET', 'POST'])
def question(id):
    form = QuestionForm()
    # q = Questions.query.filter_by(q_id=id).first()
    q = Questions.query.filter(Questions.q_id.between(1, 19 )).order_by(func.random()).first()

    if not q:
        return redirect(url_for('score'))
    if not g.user:
        return redirect(url_for('login'))
    if session['last_question'] is None:
        session['last_question'] = q.ans  
    g.user.marks = session['marks']  

    topUser = User.find_user_with_highest_marks()
    if topUser:
        print(f"Pengguna dengan marks tertinggi adalah: {topUser.username}")
        print(f"Jumlah marks: {topUser.marks}")
    else:
        topUser = User(username="Belum ada",marks=0)

    if request.method == 'POST':
        g.user.marks = session['marks']
        option = request.form['options']
        print("ini pilihan pengguna : " + option)
        print("ini jawaban yang benar : " +session['last_question'])
        # if option == q.ans:

        if option == session['last_question']:
            session['marks'] += 10
            g.user.set_marks(session['marks'])
            g.user.marks = session['marks']
            db.session.commit()
        session['last_question'] = None           

        return redirect(url_for('question', id=(id+1)))
    
    #MENAMPILKAN OPTION
    form.options.choices = [(q.a, q.a), (q.b, q.b), (q.c, q.c), (q.d, q.d)]
    return render_template('question.html', form=form, q=q, title='Question {}'.format(id),topUser=topUser)

   
@app.route('/score')
def score():
    if not g.user:
        return redirect(url_for('login'))
    g.user.marks = session['marks']

    topUser = User.find_user_with_highest_marks()
    if topUser:
        print(f"Pengguna dengan marks tertinggi adalah: {topUser.username}")
        print(f"Jumlah marks: {topUser.marks}")
    else:
        topUser = User(username="Belum ada",marks=0)

    return render_template('score.html', title='Final Score',topUser=topUser)

@app.route('/logout')
def logout():
    if not g.user:
        return redirect(url_for('login'))
    session.pop('user_id', None)
    session.pop('marks', None)
    session.pop('last_question',None)
    return redirect(url_for('home'))

@app.route('/delete/<name>')
def delete_city( name ):
    city = City.query.filter_by(name=name).first()
    db.session.delete(city)
    db.session.commit()
    flash(f'Berhasil dihapus { city.name }!', 'success')
    weather_data = query_city_weather()
    return render_template('index.html', title='Beranda',weather_data=weather_data)



