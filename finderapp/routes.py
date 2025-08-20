from flask import  render_template,request,flash,redirect,url_for
from finderapp import app,db,bcrypt
import requests,re
from finderapp.forms import RegistrationForm,LoginForm
from finderapp.models import Users,Universities,Favorites
from flask_login import login_user,current_user,logout_user
from sqlalchemy.exc import IntegrityError



@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')



@app.route('/search', methods=['GET','POST'])
def search():
    # 1. Get country
    if request.method == 'POST':
        country = request.form.get('country')
        # Redirect to GET URL so the country persists in query string
        return redirect(url_for('search', country=country))
    else:
        country = request.args.get('country')  # from URL query string
        if not country:
            flash("Please enter a country to search.")
            return redirect(url_for('home'))

    # 2. Call API and store universities in DB
    api_url = f"http://universities.hipolabs.com/search?country={country}"
    response = requests.get(api_url)
    if response.status_code != 200:
        return "API ERROR", 500

    raw_data = response.json()
    for item in raw_data:
        uni_name = item['name']
        located_country = item['country']
        uni_domain = item['domains'][0]
        uni_website = item['web_pages'][0]
        with db.session.no_autoflush:
            existing_uni = Universities.query.filter_by(domain=uni_domain,website=uni_website).first()
        if not existing_uni:
            university_add = Universities(name=uni_name, domain=uni_domain, website=uni_website, country=located_country)
            db.session.add(university_add)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()    

    # 3. Retrieve universities from DB to display
    universities = Universities.query.filter(Universities.country.ilike(f"%{country.strip()}%")).all()
    return render_template('result.html', universities=universities, country=country)




@app.route('/registration', methods=['POST'])
def register():
    if current_user.is_authenticated:
         return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user_add = Users(username = form.username.data, email = form.email.data, password = hashed_password)
        db.session.add(user_add)
        db.session.commit()
        flash(f'Your account has been created!You can now log in')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
         return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
            login_identifier = form.login.data.strip()
            if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",login_identifier):
                 user = Users.query.filter_by(email=login_identifier).first()
            else:
                 user = Users.query.filter_by(username=login_identifier).first()

            if user and bcrypt.check_password_hash(user.password,form.password.data):
                 login_user(user,remember=form.remember.data)          
                 flash(f'You have been logged in')
                 return redirect(url_for('home'))    
            else:
                 flash('Login Unsuccesful.Please check your username and password')
    return render_template('login.html',form=form)

@app.route('/logout')
def logout():
     logout_user()  
     return redirect(url_for('login')) 



@app.route('/favorite/<int:uni_id>', methods=['POST'])
def favorite(uni_id):
    if not current_user.is_authenticated:
        flash("Please log in to add favorites.")
        return redirect(url_for('login'))

    # Add favorite if not already present
    existing = Favorites.query.filter_by(user_id=current_user.id, university_id=uni_id).first()
    if not existing:
        favorite_add = Favorites(user_id=current_user.id, university_id=uni_id)
        db.session.add(favorite_add)
        db.session.commit()
        flash("Added to favorites!")
    else:
        flash("University already in favorites.")

    # Read country from POST form so search page can reload correctly
    country = request.form.get('country')
    return redirect(url_for('search', country=country))

@app.route('/favorites', methods=['GET'])
def favorites():
    if not current_user.is_authenticated:
        flash("You need to log in to view favorites.")
        return redirect(url_for('login'))
    
    
    favorites = Favorites.query.filter_by(user_id=current_user.id).all()
    
    return render_template('favorites.html', favorites=favorites)
