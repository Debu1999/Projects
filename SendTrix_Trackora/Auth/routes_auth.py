from flask_server import app
from .auth import get_login_url,authenticate_from_code
from flask import redirect,flash,request,url_for,session,render_template

from functools import wraps

def login_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login_microsoft"))
        return view_function(*args, **kwargs)
    return wrapper
@app.route("/login")
def login_microsoft():
 
    try:
        login_url = get_login_url()
        return redirect(login_url)
 
    except Exception as e:
        flash(f"Login failed: {str(e)}")
        return redirect(url_for("dashboard"))
@app.route("/auth/callback")
def auth_callback():
 
    if request.args.get("error"):
        error_description = request.args.get(
            "error_description",
            request.args.get("error")
        )
 
        flash(f"Microsoft login failed: {error_description}")
        return redirect(url_for("dashboard"))
 
    code = request.args.get("code")
 
    if not code:
        flash("Microsoft login failed: authorization code missing.")
        return redirect(url_for("dashboard"))
 
    try:
 
        result, user_id = authenticate_from_code(code)
 
        session["user_id"] = user_id
 
        print("SendTrix user ID:", user_id)
 
        flash("Microsoft login successful.")
 
        return redirect(url_for("dashboard"))
 
    except Exception as e:
 
        print("AUTH CALLBACK ERROR:", str(e))
 
        flash(f"Login failed: {str(e)}")
 
        return redirect(url_for("dashboard"))
 
@app.route("/me")
def current_user():
    user_id = session.get("user_id")
 
    return {
        "session_user_id": user_id
    }
@app.route("/logout")
def logout():
    session.clear()
 
    #flash("You have been logged out.")
 
    return redirect(url_for("logged_out"))
@app.route("/logged-out")
def logged_out():
    return render_template("logged_out.html")