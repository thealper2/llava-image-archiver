/**
 * Handles DOM content loaded event to set up various UI interactions including:
 * - Directory scan form submission
 * - Alert message display
 * - Semantic search similarity visualization animations
 */
document.addEventListener('DOMContentLoaded', function () {
    /**
     * Handle directory scan form submission
     * - Validates directory path input
     * - Shows scan progress UI
     * - Sends scan request to server
     * - Handles response and updates UI accordingly
     * - Manages form state during processing
     */
    const scanForm = document.getElementById('scan-form');
    if (scanForm) {
        scanForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const directoryInput = document.getElementById('directory');
            const directoryPath = directoryInput.value.trim();

            if (!directoryPath) {
                showAlert('Please enter a valid directory path.', 'error');
                return;
            }

            // Show scan status
            const scanStatus = document.getElementById('scan-status');
            scanStatus.classList.remove('hidden', 'success', 'error');

            const progressBar = scanStatus.querySelector('.progress-bar');
            progressBar.style.width = '0%';

            const statusMessage = document.getElementById('status-message');
            statusMessage.textContent = 'Scanning directory...';

            // Prepare form data
            const formData = new FormData();
            formData.append('directory', directoryPath);

            // Send scan request
            fetch('/scan', {
                method: 'POST',
                body: formData
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }

                    // Update progress bar to 100%
                    progressBar.style.width = '100%';

                    // Show success message
                    scanStatus.classList.add('success');
                    statusMessage.textContent = `Successfully processed ${data.processed_count} images in ${data.elapsed_time.toFixed(2)} seconds.`;

                    // Enable form again
                    scanForm.querySelectorAll('input, button').forEach(el => {
                        el.disabled = false;
                    });
                })
                .catch(error => {
                    // Show error
                    scanStatus.classList.add('error');
                    statusMessage.textContent = `Error: ${error.message}`;

                    // Enable form again
                    scanForm.querySelectorAll('input, button').forEach(el => {
                        el.disabled = false;
                    });
                });

            // Simulate progress (since we don't have real-time progress)
            let progress = 0;
            const progressInterval = setInterval(() => {
                if (progress >= 90) {
                    clearInterval(progressInterval);
                }
                progress += 5;
                progressBar.style.width = `${progress}%`;
            }, 500);

            // Disable form inputs during processing
            scanForm.querySelectorAll('input, button').forEach(el => {
                el.disabled = true;
            });
        });
    }

    /**
     * Displays a temporary alert message on the page
     * @param {string} message - The message to display
     * @param {string} type - The type of alert ('info', 'error', 'success' etc.)
     */
    function showAlert(message, type = 'info') {
        const alertBox = document.createElement('div');
        alertBox.className = `alert alert-${type}`;
        alertBox.textContent = message;

        // Add to page
        document.querySelector('.container').prepend(alertBox);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            alertBox.remove();
        }, 5000);
    }

    /**
     * Handles semantic search similarity visualization by animating the similarity bars
     * - Resets bars to 0% width
     * - Animates them to their target width with a slight delay for visual effect
     */
    const similarityBars = document.querySelectorAll('.similarity-bar');
    if (similarityBars.length > 0) {
        // Add a slight delay for animation effect
        setTimeout(() => {
            similarityBars.forEach(bar => {
                const widthValue = bar.style.width;
                bar.style.width = '0%';

                setTimeout(() => {
                    bar.style.width = widthValue;
                }, 100);
            });
        }, 300);
    }
});