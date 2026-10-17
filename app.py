import os
from datetime import date

import pymysql
from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from passlib.hash import sha256_crypt
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

# ------------------------------------------------------------------
# Configuration MySQL (XAMPP : root sans mot de passe par defaut)
# Si ton root a un mot de passe, modifie DB_PASSWORD ci-dessous.
# ------------------------------------------------------------------
DB_USER = "root"
DB_PASSWORD = ""
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "scol"

DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)


def creer_base_si_absente():
    """Cree la base 'scol' si elle n'existe pas (MySQL uniquement)."""
    if not DATABASE_URI.startswith("mysql"):
        return
    try:
        cn = pymysql.connect(host=DB_HOST, port=DB_PORT,
                             user=DB_USER, password=DB_PASSWORD)
    except pymysql.err.OperationalError as e:
        raise SystemExit(
            "\n[ERREUR] Connexion MySQL impossible : %s\n"
            "-> Lance MySQL dans XAMPP (bouton Start) et verifie "
            "DB_USER / DB_PASSWORD en haut de app.py.\n" % e
        )
    with cn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                    "CHARACTER SET utf8mb4")
    cn.commit()
    cn.close()


creer_base_si_absente()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI   # Partie 1 - question 1
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "cle-secrete-tp-flask"      # necessaire pour Flask-WTF

db = SQLAlchemy(app)
app.app_context().push()                               # Partie 1 - question 2


# ------------------------------------------------------------------
# Modeles
# ------------------------------------------------------------------
class User(db.Model):                                  # question 3
    __tablename__ = "user"
    username = db.Column(db.String(50), primary_key=True)
    email = db.Column(db.String(100))
    password = db.Column(db.String(255))


class Classe(db.Model):                                # question 5
    __tablename__ = "classe"
    CodClass = db.Column(db.String(20), primary_key=True)
    NomClasse = db.Column(db.String(50))
    NbrEtud = db.Column(db.Integer)
    etudiants = db.relationship("Etudiant", back_populates="classe")


class Etudiant(db.Model):
    __tablename__ = "etudiant"
    NCE = db.Column(db.String(20), primary_key=True)
    Nom = db.Column(db.String(50))
    Prenom = db.Column(db.String(50))
    DateNais = db.Column(db.Date)
    LieuNais = db.Column(db.String(50))
    CodClass = db.Column(
        db.String(20),
        db.ForeignKey("classe.CodClass", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    classe = db.relationship("Classe", back_populates="etudiants")
    absences = db.relationship("Absence", back_populates="etudiant")


class Matiere(db.Model):
    __tablename__ = "matiere"
    CodMat = db.Column(db.String(20), primary_key=True)
    IntMat = db.Column(db.String(100))
    Description = db.Column(db.String(255))
    absences = db.relationship("Absence", back_populates="matiere")


class Absence(db.Model):
    __tablename__ = "absence"
    CodMat = db.Column(
        db.String(20),
        db.ForeignKey("matiere.CodMat", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    NCE = db.Column(
        db.String(20),
        db.ForeignKey("etudiant.NCE", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    DateA = db.Column(db.Date, primary_key=True)
    NHA = db.Column(db.Float)
    matiere = db.relationship("Matiere", back_populates="absences")
    etudiant = db.relationship("Etudiant", back_populates="absences")


db.create_all()


def inserer_donnees_test():
    """Insere l'exemple de l'enonce, une seule fois."""
    if db.session.get(Etudiant, "E1"):
        return
    db.session.add_all([
        Classe(CodClass="C1", NomClasse="IngTA2-D", NbrEtud=25),
        Matiere(CodMat="ThGraphe", IntMat="Theorie des graphes", Description=""),
        Matiere(CodMat="ProgWebPyt", IntMat="Programmation Web Python", Description=""),
    ])
    db.session.flush()
    db.session.add(Etudiant(NCE="E1", Nom="Ben Foulen1", Prenom="Foulen1",
                            DateNais=date(2003, 5, 10), LieuNais="Tunis",
                            CodClass="C1"))
    db.session.flush()
    for cod, d, nha in [
        ("ThGraphe", date(2025, 11, 8), 1.45),
        ("ThGraphe", date(2025, 11, 15), 3.30),
        ("ProgWebPyt", date(2026, 1, 3), 1.45),
        ("ProgWebPyt", date(2026, 1, 10), 1.45),
        ("ProgWebPyt", date(2026, 1, 17), 1.45),
    ]:
        db.session.add(Absence(CodMat=cod, NCE="E1", DateA=d, NHA=nha))
    db.session.commit()


inserer_donnees_test()


# ------------------------------------------------------------------
# Formulaires (Flask-WTF) avec validation
# ------------------------------------------------------------------
class UserForm(FlaskForm):
    username = StringField("Nom d'utilisateur",
                           validators=[DataRequired(message="Ce champ est obligatoire."), Length(min=3, max=50, message="Entre 3 et 50 caractères.")])
    email = StringField("Email", validators=[DataRequired(message="Ce champ est obligatoire."), Email(message="Adresse email invalide.")])
    password = PasswordField("Mot de passe",
                             validators=[DataRequired(message="Ce champ est obligatoire."), Length(min=6, message="Au moins 6 caractères.")])
    confirm = PasswordField("Confirmer le mot de passe",
                            validators=[DataRequired(message="Ce champ est obligatoire."), EqualTo("password",
                                        message="Les mots de passe sont différents.")])
    submit = SubmitField("Ajouter")

    def validate_username(self, field):
        if db.session.get(User, field.data):
            raise ValidationError("Ce nom d'utilisateur existe déjà.")


class ChoixEtudiantForm(FlaskForm):
    nce = StringField("Numéro de carte étudiant (NCE)", validators=[DataRequired(message="Ce champ est obligatoire.")])
    submit = SubmitField("Afficher les absences")

    def validate_nce(self, field):
        if not db.session.get(Etudiant, field.data):
            raise ValidationError("Étudiant introuvable.")


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/add_user_simple/<username>/<email>/<password>")   # question 4
def add_user_simple(username, email, password):
    if db.session.get(User, username):
        return f"L'utilisateur {username} existe deja"
    db.session.add(User(username=username, email=email,
                        password=sha256_crypt.hash(password)))
    db.session.commit()
    return f"Utilisateur {username} ajoute"


@app.route("/add_user", methods=["GET", "POST"])
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        db.session.add(User(username=form.username.data,
                            email=form.email.data,
                            password=sha256_crypt.hash(form.password.data)))
        db.session.commit()
        flash("Utilisateur ajouté avec succès", "success")
        return redirect(url_for("add_user"))
    return render_template("add_user.html", form=form)


@app.route("/users")
def users():
    return render_template("users.html", users=User.query.all())


@app.route("/choisir", methods=["GET", "POST"])
def choisir_etudiant():
    form = ChoixEtudiantForm()
    if form.validate_on_submit():
        return redirect(url_for("absences_etudiant", nce=form.nce.data))
    return render_template("choisir_etudiant.html", form=form)


@app.route("/absences/<nce>")                                  # question 6
def absences_etudiant(nce):
    etudiant = Etudiant.query.get_or_404(nce)
    absences = (Absence.query.filter_by(NCE=nce)
                .order_by(Absence.DateA).all())
    return render_template("absence_etudiant.html",
                           etudiant=etudiant, absences=absences)


if __name__ == "__main__":
    app.run(debug=True)
