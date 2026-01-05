from app import create_app

app = create_app('development')

if __name__ == '__main__':
    # Using port 5001 to avoid conflict with macOS AirPlay on port 5000
    app.run(host='0.0.0.0', port=5001, debug=True)
