import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI='sqlite:///site.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER='uploads',
    SECRET_KEY='your_secret_key',
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif'}
)
db = SQLAlchemy(app)

class ImagePost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    tags = db.Column(db.String(200), nullable=True)

    # Tambahkan relasi
    comments = db.relationship('Comment', backref='image_post', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_id = db.Column(db.Integer, db.ForeignKey('image_post.id'), nullable=False)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Tidak ada file yang diunggah', 'error')
            return redirect(request.url)

        file = request.files['file']
        if not file or not allowed_file(file.filename):
            flash('Ekstensi file tidak diizinkan atau tidak ada file', 'error')
            return redirect(request.url)

        file.seek(0, os.SEEK_END)
        if file.tell() > 5 * 1024 * 1024:  # 5 MB
            flash('Ukuran file terlalu besar. Maksimal 5 MB.', 'error')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        img = Image.open(file)
        img.thumbnail((800, 800))
        img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        tags_input = request.form.get('tags', '')
        new_image = ImagePost(filename=filename, tags=tags_input)
        db.session.add(new_image)
        db.session.commit()
        flash('Meme berhasil diunggah', 'success')
        return redirect(url_for('index'))

    images = ImagePost.query.order_by(ImagePost.timestamp.desc()).paginate(page=request.args.get('page', 1, type=int), per_page=10)
    return render_template('index.html', images=images)

@app.route('/image/<int:image_id>', methods=['GET', 'POST'])
def image(image_id):
    image_post = ImagePost.query.get_or_404(image_id)
    if request.method == 'POST':
        comment_text = request.form.get('comment')
        if comment_text:
            new_comment = Comment(text=comment_text, image_id=image_post.id)
            db.session.add(new_comment)
            db.session.commit()
            flash('Komentar berhasil ditambahkan', 'success')
            return redirect(url_for('image', image_id=image_id))

    # Akses komentar dari relasi
    comments_list = image_post.comments  # Ubah ini
    return render_template('image.html', image=image_post, comments_list=comments_list)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/like/<int:image_id>')
def like_image(image_id):
    image = ImagePost.query.get_or_404(image_id)
    image.likes += 1
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/gallery')
def gallery():
    images = ImagePost.query.all()
    return render_template('gallery.html', images=images)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)