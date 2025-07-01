# 🌿 WildCards  
**Team 24 – WikiVerse Hackathon 2025 @ IIIT-Hyderabad**  
> Built entirely with open-source tools.

WildCards is a lightweight web app that turns species names into interactive flashcards.  
It pulls real-time data from *Wikispecies* and *Wikimedia Commons* to help users quickly learn about animals, plants, fungi, and more.

---

## 🚀 Why WildCards?

Most species databases are either too scientific or hard to navigate.  
WildCards was built to **simplify biodiversity education** for:

- 🌱 Students  
- 🧠 Self-learners  
- 🐾 Nature enthusiasts  

> 🧠 **Enter a species name, and instantly get:**  
> ✅ Flashcards for taxonomic hierarchy (Kingdom → Species)  
> ✅ Common names (multi-language support)  
> ✅ Real images from Wikimedia Commons  

---

## 🛠️ Tech Stack (100% Open Source)

| Layer        | Technology               |
|--------------|---------------------------|
| Frontend     | HTML, CSS, JavaScript     |
| Backend      | Python (Flask)            |
| Data Source  | Wikispecies API           |
| Media Source | Wikimedia Commons API     |
| License      | MIT                       |

---

## ✨ Features

- 🔍 **Species Search** – Just type the name and go  
- 🧬 **Flashcard Generator** – Taxonomy simplified visually  
- 🖼️ **Live Images** – Pulled directly from Wikimedia Commons  
- 🌐 **Language Support** – Hindi, Telugu, and more  
- 📱 **Responsive UI** – Works across mobile and desktop  
- 🧩 **Open Source** – Built using only free tools

---

## 🔗 APIs Used

### 📚 Wikispecies API

```
GET https://species.wikimedia.org/w/api.php?action=parse&page={species_name}&format=json
```

- Fetches scientific classification hierarchy.

---

### 🖼️ Wikimedia Commons API

```
GET https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={species_name}&prop=imageinfo&iiprop=url
```

- Fetches relevant public domain images of species.

---

## 🧪 Example Output

**Input**: `Canis lupus` *(Gray Wolf)*

```
Q: What family does Canis lupus belong to?
A: Canidae

Q: What is the kingdom?
A: Animalia

Image: High-res wolf image from Wikimedia Commons
```

---

## 🧰 Running Locally

```bash
# 1. Clone the repository
git clone https://code.swecha.org/soai2025/soai-hackathon/hackathon-group-24.git

# 2. (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the Flask server
python app.py
```

Then open your browser at:  
[http://localhost:5000](http://localhost:5000)

---

## 📝 License

This project is licensed under the **MIT License**.  
You are free to fork, modify, and contribute.

---

## 🙌 Acknowledgements

- [Wikispecies](https://species.wikimedia.org/)  
- [Wikimedia Commons](https://commons.wikimedia.org/)    
- [Flask](https://flask.palletsprojects.com/)  
- [IIIT-H WikiVerse Hackathon 2025](https://meta.wikimedia.org/wiki/)
