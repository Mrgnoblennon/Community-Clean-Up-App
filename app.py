from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
  return render_template("index.html")

@app.route("/events")
def events():
    cleanup_events = [
        {
            "name": "Riverside Park Clean-Up",
            "date": "24 October 2026",
            "time": "10:00 AM - 12:00 PM",
            "registered": 12,
            "capacity": 20
        },
        {
            "name": "The Esplanade Gathering",
            "date": "14 November 2026",
            "time": "9:00 AM - 11:00 AM",
            "registered": 6,
            "capacity": 15
        },
        {
            "name": "Fringe Presents: Community",
            "date": "14 November 2026",
            "time": "9:00 AM - 11:00 AM",
            "registered": 6,
            "capacity": 15
        }
    ]

    return render_template("events.html", events=cleanup_events)

if __name__ == "__main__":
    app.run(debug=True)