from flask import  render_template,request,flash,redirect,url_for,jsonify
from finderapp import app,db,bcrypt
import requests,re
from finderapp.forms import RegistrationForm,LoginForm
from finderapp.models import Users,Universities,Favorites
from flask_login import login_user,current_user,logout_user
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import create_access_token,jwt_required,get_jwt_identity



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
    # 4. Collect user's favorites
    if current_user.is_authenticated:
        user_favorite_ids = [fav.university_id for fav in Favorites.query.filter_by(user_id=current_user.id).all()]
    else:
        user_favorite_ids = []

    return render_template('result.html', universities=universities, country=country,user_favorite_ids=user_favorite_ids)


@app.route('/api/universities',methods=['GET'])
@jwt_required()
def get_universities():
    user_id = get_jwt_identity()
    country = request.args.get('country')

    if not country:
        return jsonify({"error": "Country parameter required"}), 400

    results = Universities.query.filter(Universities.country.ilike(f"%{country.strip()}%")).all()

    if  results:
        return jsonify([u.to_dict() for u in results])
    
    api_url = f"http://universities.hipolabs.com/search?country={country}"
    response = requests.get(api_url)
    if response.status_code != 200:
        return jsonify({"error": "External API Request Failed"}), 502
    
    raw_data = response.json()
    for item in raw_data:
        uni_name = item['name']
        located_country = item['country']
        uni_domain = item.get('domains',[None])[0]
        uni_website = item.get('web_pages',[None])[0]
        with db.session.no_autoflush:
            existing_uni = Universities.query.filter_by(domain=uni_domain,website=uni_website).first()
        if not existing_uni:
            university_add = Universities(name=uni_name, domain=uni_domain, website=uni_website, country=located_country)
            db.session.add(university_add)
        
    try:
            db.session.commit()
    except IntegrityError:
            db.session.rollback()    

    results = Universities.query.filter(Universities.country.ilike(f"%{country.strip()}%")).all()        
    return jsonify([u.to_dict() for u in results])

    




@app.route('/registration', methods=['POST','GET'])
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

@app.route('/api/registration', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not username or not email or not password:
        return jsonify({"error": "Username,email and password are required"}), 401
    
    existing_user = Users.query.filter(
        (Users.username == username) | (Users.email == email)
    ).first()

    if existing_user:
        return jsonify({"error": "User already exist"})
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = Users(username = username, email = email, password = hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({
        "message": "Your account has been created!You can now login",
        "user":{
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }
        }), 201


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

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()

    if not data or "login" not in data or "password" not in data:
        return jsonify({"error": "Missing username/email or password"}), 400

    login_identifier = data["login"].strip()
    password = data["password"]

    if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",login_identifier):
        user = Users.query.filter_by(email=login_identifier).first()
    else:
        user = Users.query.filter_by(username=login_identifier).first()

    if user and bcrypt.check_password_hash(user.password,password):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "message": "Login Successful",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            } 
        })
    return jsonify({"error": "Invalid credentials"}), 400           

@app.route('/logout')
def logout():
     logout_user()  
     return redirect(url_for('login')) 

@app.route('/api/logout', methods=['Post'])
def api_logout(): 
     return jsonify({"message": "Logged out successfully"}), 200 


@app.route('/favorite/<int:uni_id>', methods=['POST'])
def favorite(uni_id):
    if not current_user.is_authenticated:
        flash("Please log in to add favorites.")
        return redirect(url_for('login'))

    # Add favorite if not already present
    existing_favorite = Favorites.query.filter_by(user_id=current_user.id, university_id=uni_id).first()
    if not existing_favorite:
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
    
    return render_template('favorite.html', favorites=favorites)


@app.route('/api/favorites', methods=['POST'])
@jwt_required()
def api_add_favorite():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data or "university_id" not in data:
        return jsonify({"error": "University_id is required"}), 400
    
    existing_favorite = Favorites.query.filter_by(user_id=user_id, university_id=data["university_id"]).first()
    
    if existing_favorite:
        return jsonify({"error": "Already in favorites"}), 200
    

    new_favorite = Favorites(user_id=user_id,university_id = data["university_id"])
    db.session.add(new_favorite)
    db.session.commit()
    return jsonify({
        "message": "Favorite added successfully",
        "favorite": new_favorite.to_fav()
    }), 201

@app.route('/api/favorites',methods=['GET'])
@jwt_required()
def get_favorites():
    user_id = get_jwt_identity()
    result = Favorites.query.filter_by(user_id=user_id).all()
    
    return jsonify([f.to_fav() for f in result])


@app.route('/remove_favorite/<int:uni_id>', methods=['POST'])
def remove_favorite(uni_id):
    if not current_user.is_authenticated:
        flash('Please login to remove from favorites')
        return redirect(url_for('login'))

    exsiting_favorite = Favorites.query.filter_by(user_id= current_user.id,university_id=uni_id).first()
    if exsiting_favorite:
        db.session.delete(exsiting_favorite)
        db.session.commit()
        flash('University removed from favorites')

    next_page = request.form.get('next')
    if next_page == 'favorites':
        return redirect(url_for('favorites'))
    else:
        country=request.form.get('country')
        return redirect(url_for('search',country=country)) 
    

@app.route('/api/remove_favorite/<int:favorite_id>', methods=['DELETE'])
@jwt_required()
def delete_favorite(favorite_id):
    user_id = get_jwt_identity()
    delete_fav = Favorites.query.filter_by(id=favorite_id,user_id=user_id).first()
    if not delete_fav:
        return jsonify({"error": "Favorite not found"}), 404

    db.session.delete(delete_fav)
    db.session.commit()

    return jsonify({"message": "Favorite removed successfully"}), 200   


@app.route('/api/refresh',methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    
    return jsonify(access_token=access_token)
