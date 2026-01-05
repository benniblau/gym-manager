// Workout Edit Page JavaScript
// Handles exercise search, filtering, adding, removing, and reordering

document.addEventListener('DOMContentLoaded', function() {
    const exerciseSearch = document.getElementById('exercise-search');
    const categoryFilter = document.getElementById('category-filter');
    const muscleFilter = document.getElementById('muscle-filter');
    const exerciseItems = document.querySelectorAll('.exercise-item');

    // Search and filter functionality
    function filterExercises() {
        const searchTerm = exerciseSearch.value.toLowerCase();
        const selectedCategory = categoryFilter.value;
        const selectedMuscle = muscleFilter.value;

        exerciseItems.forEach(item => {
            const exerciseName = item.querySelector('h6').textContent.toLowerCase();
            const exerciseCategory = item.getAttribute('data-category') || '';
            const exerciseMuscles = item.getAttribute('data-muscle') || '';

            const matchesSearch = exerciseName.includes(searchTerm);
            const matchesCategory = !selectedCategory || exerciseCategory === selectedCategory;
            // For muscles, check if the selected muscle is in the comma-separated list
            const matchesMuscle = !selectedMuscle || exerciseMuscles.split(', ').includes(selectedMuscle);

            if (matchesSearch && matchesCategory && matchesMuscle) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }

    // Add event listeners for search and filters
    if (exerciseSearch) {
        exerciseSearch.addEventListener('input', filterExercises);
    }
    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterExercises);
    }
    if (muscleFilter) {
        muscleFilter.addEventListener('change', filterExercises);
    }

    // View exercise details button click handler
    document.querySelectorAll('.view-exercise-details').forEach(button => {
        button.addEventListener('click', async function() {
            const exerciseId = this.getAttribute('data-exercise-id');
            const exerciseName = this.getAttribute('data-exercise-name');

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('exerciseDetailsModal'));
            modal.show();

            // Reset modal state
            document.getElementById('details-exercise-name').textContent = exerciseName;
            document.getElementById('details-loading').style.display = 'block';
            document.getElementById('details-content').style.display = 'none';
            document.getElementById('details-error').style.display = 'none';

            try {
                // Fetch exercise details
                const response = await fetch(`/exercises/${exerciseId}/details`);
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                // Hide loading, show content
                document.getElementById('details-loading').style.display = 'none';
                document.getElementById('details-content').style.display = 'block';

                // Populate modal with data
                document.getElementById('details-category').textContent = data.category_name || '';
                document.getElementById('details-muscles').textContent = data.primary_muscles || '';
                document.getElementById('details-description').textContent = data.description || 'No description available';

                // Images
                const imagesContainer = document.getElementById('details-images-container');
                const image1Container = document.getElementById('details-image1-container');
                const image2Container = document.getElementById('details-image2-container');

                let hasImages = false;
                if (data.image1_url) {
                    document.getElementById('details-image1').src = data.image1_url;
                    image1Container.style.display = 'block';
                    hasImages = true;
                } else {
                    image1Container.style.display = 'none';
                }

                if (data.image2_url) {
                    document.getElementById('details-image2').src = data.image2_url;
                    image2Container.style.display = 'block';
                    hasImages = true;
                } else {
                    image2Container.style.display = 'none';
                }

                imagesContainer.style.display = hasImages ? 'block' : 'none';

                // Instructions
                const instructionsContainer = document.getElementById('details-instructions-container');
                const instructionsList = document.getElementById('details-instructions');
                if (data.instructions && data.instructions.length > 0) {
                    instructionsList.innerHTML = '';
                    data.instructions.forEach(instruction => {
                        const li = document.createElement('li');
                        li.textContent = instruction;
                        instructionsList.appendChild(li);
                    });
                    instructionsContainer.style.display = 'block';
                } else {
                    instructionsContainer.style.display = 'none';
                }

                // Equipment
                const equipmentContainer = document.getElementById('details-equipment-container');
                if (data.equipment && data.equipment.length > 0) {
                    document.getElementById('details-equipment').textContent = data.equipment.join(', ');
                    equipmentContainer.style.display = 'block';
                } else {
                    equipmentContainer.style.display = 'none';
                }

                // External links
                const videoLink = document.getElementById('details-video-link');
                if (data.video) {
                    videoLink.href = data.video;
                    videoLink.style.display = 'inline-block';
                } else {
                    videoLink.style.display = 'none';
                }

                // Exercem link (using exercem_url helper)
                const exercemLink = document.getElementById('details-exercem-link');
                exercemLink.href = `https://exercem.us/exercises/${encodeURIComponent(data.name.toLowerCase().replace(/ /g, '-'))}`;

                // Garmin link
                const garminLink = document.getElementById('details-garmin-link');
                if (data.garmin_url) {
                    garminLink.href = data.garmin_url;
                    garminLink.style.display = 'inline-block';
                } else {
                    garminLink.style.display = 'none';
                }

            } catch (error) {
                console.error('Error fetching exercise details:', error);
                document.getElementById('details-loading').style.display = 'none';
                document.getElementById('details-error').style.display = 'block';
            }
        });
    });

    // Edit exercise button click handler
    document.querySelectorAll('.edit-exercise').forEach(button => {
        button.addEventListener('click', function() {
            const exerciseId = this.getAttribute('data-exercise-id');
            const exerciseName = this.getAttribute('data-exercise-name');
            const targetSets = this.getAttribute('data-target-sets');
            const targetReps = this.getAttribute('data-target-reps');
            const targetWeight = this.getAttribute('data-target-weight');
            const targetDuration = this.getAttribute('data-target-duration');
            const notes = this.getAttribute('data-notes');

            // Show modal with current values
            document.getElementById('modal-exercise-name').textContent = exerciseName;
            document.getElementById('modal-exercise-id').value = exerciseId;

            // Populate form with existing values (use actual values, don't default)
            document.getElementById('target-sets').value = targetSets || '';
            document.getElementById('target-reps').value = targetReps || '';
            document.getElementById('target-weight').value = targetWeight || '';
            document.getElementById('target-duration').value = targetDuration || '';
            document.getElementById('exercise-notes').value = notes || '';

            // Change modal title and button text for editing
            document.querySelector('#exerciseModal .modal-title').textContent = 'Edit Exercise';
            document.getElementById('confirm-add-exercise').textContent = 'Update Exercise';
            document.getElementById('confirm-add-exercise').setAttribute('data-mode', 'edit');

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('exerciseModal'));
            modal.show();
        });
    });

    // Add exercise button click handler
    document.querySelectorAll('.add-exercise').forEach(button => {
        button.addEventListener('click', function() {
            const exerciseId = this.getAttribute('data-exercise-id');
            const exerciseName = this.getAttribute('data-exercise-name');

            // Show modal with exercise details
            document.getElementById('modal-exercise-name').textContent = exerciseName;
            document.getElementById('modal-exercise-id').value = exerciseId;

            // Reset form values
            document.getElementById('target-sets').value = 3;
            document.getElementById('target-reps').value = 10;
            document.getElementById('target-weight').value = '';
            document.getElementById('target-duration').value = '';
            document.getElementById('exercise-notes').value = '';

            // Change modal title and button text for adding
            document.querySelector('#exerciseModal .modal-title').textContent = 'Add Exercise';
            document.getElementById('confirm-add-exercise').textContent = 'Add Exercise';
            document.getElementById('confirm-add-exercise').setAttribute('data-mode', 'add');

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('exerciseModal'));
            modal.show();
        });
    });

    // Helper function to get base URL (works for both /workouts and /templates)
    function getBaseUrl() {
        const pathParts = window.location.pathname.split('/');
        const baseType = pathParts[1]; // 'workouts' or 'templates'
        const id = pathParts[2];
        return `/${baseType}/${id}`;
    }

    // Confirm add/edit exercise button
    const confirmAddButton = document.getElementById('confirm-add-exercise');
    if (confirmAddButton) {
        confirmAddButton.addEventListener('click', function() {
            const baseUrl = getBaseUrl();
            const exerciseId = document.getElementById('modal-exercise-id').value;
            const targetSets = document.getElementById('target-sets').value;
            const targetReps = document.getElementById('target-reps').value;
            const targetWeight = document.getElementById('target-weight').value;
            const targetDuration = document.getElementById('target-duration').value;
            const notes = document.getElementById('exercise-notes').value;
            const mode = this.getAttribute('data-mode') || 'add';

            let url;
            if (mode === 'edit') {
                // Update existing exercise targets
                url = baseUrl.startsWith('/templates')
                    ? `/workouts${baseUrl.replace('/templates', '')}/exercises/${exerciseId}/update-targets`
                    : `${baseUrl}/exercises/${exerciseId}/update-targets`;
            } else {
                // Add new exercise
                url = baseUrl.startsWith('/templates')
                    ? `/workouts${baseUrl.replace('/templates', '')}/exercises/add`
                    : `${baseUrl}/exercises/add`;
            }

            // Send AJAX request
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'exercise_id': exerciseId,
                    'target_sets': targetSets,
                    'target_reps': targetReps,
                    'target_weight': targetWeight,
                    'target_duration': targetDuration,
                    'notes': notes
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Close modal and reload page
                    bootstrap.Modal.getInstance(document.getElementById('exerciseModal')).hide();
                    location.reload();
                } else {
                    alert(`Error ${mode === 'edit' ? 'updating' : 'adding'} exercise: ` + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                alert(`Error ${mode === 'edit' ? 'updating' : 'adding'} exercise: ` + error);
            });
        });
    }

    // Remove exercise button click handler
    document.querySelectorAll('.remove-exercise').forEach(button => {
        button.addEventListener('click', function() {
            if (!confirm('Remove this exercise from the workout?')) {
                return;
            }

            const baseUrl = getBaseUrl();
            const exerciseId = this.getAttribute('data-exercise-id');

            // Determine correct endpoint
            const removeUrl = baseUrl.startsWith('/templates')
                ? `/workouts${baseUrl.replace('/templates', '')}/exercises/${exerciseId}/remove`
                : `${baseUrl}/exercises/${exerciseId}/remove`;

            fetch(removeUrl, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error removing exercise: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                alert('Error removing exercise: ' + error);
            });
        });
    });

    // Reorder exercise button click handler
    document.querySelectorAll('.reorder-exercise').forEach(button => {
        button.addEventListener('click', function() {
            const baseUrl = getBaseUrl();
            const exerciseId = this.getAttribute('data-exercise-id');
            const direction = this.getAttribute('data-direction');

            // Determine correct endpoint
            const reorderUrl = baseUrl.startsWith('/templates')
                ? `/workouts${baseUrl.replace('/templates', '')}/exercises/${exerciseId}/reorder`
                : `${baseUrl}/exercises/${exerciseId}/reorder`;

            fetch(reorderUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'direction': direction
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error reordering exercise: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                alert('Error reordering exercise: ' + error);
            });
        });
    });
});
