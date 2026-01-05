# Gym Manager

A comprehensive Flask-based web application for managing workouts, tracking exercise progress, and syncing with Strava. Built with Python, SQLite, and Bootstrap 5, this application helps fitness enthusiasts plan, log, and analyze their training sessions.

## Features

### 🏋️ Workout Management
- **Create Custom Workouts**: Build workouts from a library of 2000+ exercises across multiple categories
- **Workout Templates**: Create reusable workout templates for consistent training routines
- **Exercise Library**: Browse and search exercises by category, muscle group, and equipment
- **Target Values**: Set target sets, reps, weight, and duration for each exercise
- **Progress Tracking**: Log actual performance and compare against targets

### 📊 Exercise Database
- **2000+ Exercises**: Comprehensive database including:
  - Strength training exercises
  - Stretching routines
  - Plyometrics
  - Olympic weightlifting
  - Strongman exercises
  - Cardio activities
  - Calisthenics
  - CrossFit movements
- **Detailed Information**: Each exercise includes:
  - Step-by-step instructions
  - Primary and secondary muscle groups
  - Required equipment
  - Video tutorials (where available)
  - Exercise illustrations
  - Difficulty levels
  - Garmin Connect integration

### 🔄 Strava Integration
- **OAuth Authentication**: Securely connect your Strava account
- **Activity Upload**: Upload completed workouts to Strava
- **Multiple Uploads**: Re-upload workouts as needed
- **Category-Specific Emojis**: Workouts display with category-appropriate emojis (💪 for strength, 🧘 for stretching, etc.)
- **TCX Export**: Export workouts in TCX format for compatibility with other fitness platforms

### 📱 User Experience
- **Responsive Design**: Mobile-first interface optimized for gym use
- **Auto-Save**: Workout data saves automatically as you log exercises
- **Modal Interactions**: View exercise details without leaving your current page
- **Smart Filters**: Filter exercises by category, muscle, and equipment
- **Progress Visualization**: Track workout completion with visual progress bars
- **Touch-Optimized**: Large buttons and stepper controls for easy mobile use

### 👤 User Management
- **Secure Authentication**: Password hashing with bcrypt
- **User Accounts**: Individual user profiles with personalized workout history
- **Session Management**: Secure login sessions with Flask-Login

## Tech Stack

### Backend
- **Flask 3.1.2**: Python web framework
- **SQLite3**: Lightweight database
- **Flask-Login**: User session management
- **Flask-Bcrypt**: Password hashing
- **Flask-WTF**: Form handling and validation
- **Requests**: HTTP library for Strava API integration
- **Python-dotenv**: Environment variable management

### Frontend
- **Bootstrap 5**: Responsive CSS framework
- **Bootstrap Icons**: Icon library
- **Vanilla JavaScript**: No framework dependencies
- **Jinja2 Templates**: Server-side templating

### APIs & Integrations
- **Strava API**: Activity sync and OAuth
- **exercem.us**: External exercise resource links
- **Garmin Connect**: Exercise integration

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/gym-manager.git
   cd gym-manager
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set:
   - `SECRET_KEY`: Generate a secure random key
   - `STRAVA_CLIENT_ID`: Your Strava API client ID
   - `STRAVA_CLIENT_SECRET`: Your Strava API client secret
   - `STRAVA_REDIRECT_URI`: Your OAuth callback URL

5. **Initialize the database**
   ```bash
   python database.py
   ```

   This will create `exercises.db` and populate it with the exercise library.

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Access the application**

   Open your browser and navigate to: `http://localhost:5001`

## Configuration

### Strava API Setup

1. Visit [Strava API Settings](https://www.strava.com/settings/api)
2. Create a new application
3. Set the Authorization Callback Domain:
   - Local: `localhost`
   - Production: Your domain
4. Copy the Client ID and Client Secret to your `.env` file

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | `your-secret-key-here` |
| `STRAVA_CLIENT_ID` | Strava API client ID | `12345` |
| `STRAVA_CLIENT_SECRET` | Strava API client secret | `abc123...` |
| `STRAVA_REDIRECT_URI` | OAuth redirect URI | `http://localhost:5001/strava/callback` |

## Database Schema

### Core Tables

#### users
Stores user account information
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email address
- `password_hash`: Bcrypt hashed password
- `created_at`, `last_login`: Timestamps

#### workouts
Workout sessions and templates
- `id`: Primary key
- `user_id`: Foreign key to users
- `name`: Workout name
- `scheduled_date`, `scheduled_time`: When workout is planned
- `status`: planned | in_progress | completed
- `is_template`: Boolean flag for templates
- `notes`: User notes
- `started_at`, `completed_at`: Actual workout times

#### workout_exercises
Junction table linking workouts to exercises
- `workout_id`, `exercise_id`: Foreign keys
- `order_position`: Exercise order in workout
- `target_sets`, `target_reps`, `target_weight`, `target_duration`: Planned values
- `actual_sets`, `actual_reps`, `actual_weight`, `actual_duration`: Logged values
- `notes`: Exercise-specific notes

### Exercise Database Tables

#### exercises
Core exercise information
- `id`, `name`, `description`
- `category_id`: Foreign key to categories
- `video`, `image1_url`, `image2_url`: Media URLs
- `garmin_id`, `garmin_url`: Garmin integration
- `difficulty`, `focus`: Exercise metadata

#### categories
Exercise categories (Strength, Stretching, Cardio, etc.)

#### muscles
Muscle groups (Chest, Back, Legs, etc.)

#### equipment
Required equipment (Barbell, Dumbbells, etc.)

#### instructions
Step-by-step exercise instructions

### Integration Tables

#### strava_connections
Strava OAuth tokens per user
- `user_id`: Foreign key to users
- `access_token`, `refresh_token`: OAuth tokens
- `expires_at`: Token expiration
- `athlete_id`, `athlete_username`: Strava athlete info

#### strava_uploads
Track workout uploads to Strava
- `workout_id`: Foreign key to workouts
- `strava_activity_id`: Strava activity ID
- `upload_status`: success | failed
- `uploaded_at`: Upload timestamp

## Project Structure

```
gym-manager/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Configuration classes
│   ├── models.py                # Database models
│   ├── utils/                   # Utility functions
│   ├── blueprints/              # Route blueprints
│   │   ├── auth/                # Authentication routes
│   │   ├── main/                # Main/home routes
│   │   ├── workouts/            # Workout management
│   │   ├── exercises/           # Exercise browsing
│   │   ├── templates/           # Template management
│   │   └── strava/              # Strava integration
│   ├── static/                  # Static assets
│   │   ├── css/                 # Custom styles
│   │   ├── js/                  # JavaScript files
│   │   └── images/              # Exercise images
│   └── templates/               # Jinja2 templates
│       ├── base.html            # Base template
│       ├── auth/                # Auth pages
│       ├── workouts/            # Workout pages
│       ├── exercises/           # Exercise pages
│       └── templates/           # Template pages
├── venv/                        # Virtual environment
├── exercises.db                 # SQLite database
├── database.py                  # Database setup script
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
└── README.md                    # This file
```

## Usage

### Creating a Workout

1. **From Scratch**:
   - Click "New Workout" from the dashboard
   - Enter workout name, date, and optional notes
   - Add exercises from the library
   - Set target sets, reps, weight, and duration

2. **From Template**:
   - Navigate to Templates
   - Select a template and click "Use Template"
   - Choose a date and customize if needed

### Logging a Workout

1. Navigate to a planned workout
2. Click "Log Workout"
3. Enter actual values for each exercise
4. Values auto-save as you type
5. Mark workout as completed when finished

### Creating a Template

1. Create a workout with desired exercises
2. Click "Save as Template"
3. Template is now reusable for future workouts

### Syncing with Strava

1. Connect your Strava account (Settings → Strava)
2. Complete a workout
3. Click "Upload to Strava"
4. View your activity on Strava

### Browsing Exercises

1. Navigate to "Browse Exercises"
2. Use filters to narrow by:
   - Category (Strength, Cardio, etc.)
   - Muscle group
   - Equipment needed
3. Click exercise for detailed instructions and media

## API Endpoints

### Authentication
- `GET /auth/login` - Login page
- `POST /auth/login` - Process login
- `GET /auth/register` - Registration page
- `POST /auth/register` - Process registration
- `GET /auth/logout` - Logout

### Workouts
- `GET /workouts/` - List workouts
- `POST /workouts/create` - Create workout
- `GET /workouts/<id>` - View workout
- `GET /workouts/<id>/edit` - Edit workout
- `POST /workouts/<id>/update-notes` - Update notes
- `GET /workouts/<id>/log` - Log workout
- `POST /workouts/<id>/complete` - Mark complete
- `POST /workouts/<id>/delete` - Delete workout

### Templates
- `GET /templates/` - List templates
- `POST /templates/create` - Create template
- `GET /templates/<id>` - View template
- `POST /templates/<id>/update-notes` - Update notes
- `POST /templates/<id>/use` - Create workout from template

### Exercises
- `GET /exercises/` - Browse exercises
- `GET /exercises/<id>` - View exercise
- `GET /exercises/<id>/details` - Get exercise JSON

### Strava
- `GET /strava/connect` - Initiate OAuth
- `GET /strava/callback` - OAuth callback
- `POST /strava/upload/<workout_id>` - Upload workout
- `POST /strava/disconnect` - Disconnect account

## Development

### Running Tests
```bash
# Coming soon
pytest
```

### Database Migrations
```bash
# Backup current database
cp exercises.db exercises.db.backup

# Modify schema in database.py

# Recreate database
python database.py
```

### Adding Exercises
Add exercises to the database using the models:
```python
from app.models import Exercise

Exercise.create(
    name="New Exercise",
    category_id=1,
    description="Description here"
)
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Exercise data sourced from various fitness resources
- Strava API for activity integration
- Bootstrap team for the excellent CSS framework
- Flask community for comprehensive documentation

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

Built with ❤️ for fitness enthusiasts
