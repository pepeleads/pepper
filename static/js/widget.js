class PepperSurvey {
    constructor(config) {
        this.config = {
            formId: null,
            buttonText: 'Take Survey',
            buttonColor: '#1a73e8',  // Google Blue
            buttonPosition: 'bottom-right',
            buttonIcon: '📋',  // Default icon
            modalWidth: '90%',
            modalMaxWidth: '800px',
            modalHeight: '80vh',
            animationDuration: '0.3s',
            theme: 'light',  // light or dark
            customStyles: {},  // For custom CSS overrides
            ...config
        };
        
        this.init();
    }

    init() {
        this.createStyles();
        this.createFloatingButton();
        this.createModalContainer();
        this.addEventListeners();
    }

    createStyles() {
        const styleSheet = document.createElement('style');
        styleSheet.textContent = `
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            .pepper-survey-button {
                position: fixed;
                padding: 12px 24px;
                background-color: ${this.config.buttonColor};
                color: white;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 9999;
                font-family: Arial, sans-serif;
                font-size: 16px;
                transition: all ${this.config.animationDuration} ease;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .pepper-survey-button:hover {
                transform: scale(1.05);
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            }
            
            .pepper-survey-button:active {
                transform: scale(0.95);
            }
            
            .pepper-survey-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
                z-index: 10000;
                visibility: hidden;
                opacity: 0;
                transition: visibility 0s linear ${this.config.animationDuration}, 
                            opacity ${this.config.animationDuration} ease;
            }
            
            .pepper-survey-modal.visible {
                visibility: visible;
                opacity: 1;
                transition: visibility 0s linear 0s, 
                            opacity ${this.config.animationDuration} ease;
            }
            
            .pepper-survey-modal-content {
                background-color: ${this.config.theme === 'dark' ? '#1a1a1a' : 'white'};
                padding: 20px;
                border-radius: 12px;
                width: ${this.config.modalWidth};
                max-width: ${this.config.modalMaxWidth};
                max-height: 90vh;
                overflow-y: auto;
                position: relative;
                transform: translateY(20px);
                opacity: 0;
                transition: transform ${this.config.animationDuration} ease,
                            opacity ${this.config.animationDuration} ease;
                box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            }
            
            .pepper-survey-modal.visible .pepper-survey-modal-content {
                transform: translateY(0);
                opacity: 1;
            }
            
            .pepper-survey-close {
                position: absolute;
                right: 15px;
                top: 15px;
                border: none;
                background: none;
                font-size: 24px;
                cursor: pointer;
                color: ${this.config.theme === 'dark' ? '#ffffff' : '#666666'};
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
            }
            
            .pepper-survey-close:hover {
                background-color: ${this.config.theme === 'dark' ? '#333333' : '#f0f0f0'};
            }
            
            .pepper-survey-iframe {
                width: 100%;
                height: ${this.config.modalHeight};
                border: none;
                border-radius: 8px;
            }
            
            .pepper-survey-loading {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: ${this.config.theme === 'dark' ? '#ffffff' : '#666666'};
                font-size: 16px;
                animation: pulse 1.5s infinite;
            }
        `;
        document.head.appendChild(styleSheet);
    }

    createFloatingButton() {
        const button = document.createElement('button');
        button.id = 'pepper-survey-button';
        button.className = 'pepper-survey-button';
        button.innerHTML = `
            <span class="pepper-survey-icon">${this.config.buttonIcon}</span>
            <span class="pepper-survey-text">${this.config.buttonText}</span>
        `;

        // Position the button
        const position = this.config.buttonPosition.split('-');
        button.style[position[0]] = '20px';
        button.style[position[1]] = '20px';

        // Apply custom styles if provided
        Object.assign(button.style, this.config.customStyles.button || {});

        document.body.appendChild(button);
    }

    createModalContainer() {
        const modal = document.createElement('div');
        modal.id = 'pepper-survey-modal';
        modal.className = 'pepper-survey-modal';

        const modalContent = document.createElement('div');
        modalContent.className = 'pepper-survey-modal-content';

        const closeButton = document.createElement('button');
        closeButton.className = 'pepper-survey-close';
        closeButton.innerHTML = '×';
        closeButton.onclick = () => this.closeModal();

        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'pepper-survey-loading';
        loadingIndicator.textContent = 'Loading...';

        const iframe = document.createElement('iframe');
        iframe.className = 'pepper-survey-iframe';
        iframe.src = `${window.location.origin}/form/${this.config.formId}/embed`;
        iframe.onload = () => {
            loadingIndicator.style.display = 'none';
        };

        modalContent.appendChild(closeButton);
        modalContent.appendChild(loadingIndicator);
        modalContent.appendChild(iframe);
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
    }

    addEventListeners() {
        const button = document.getElementById('pepper-survey-button');
        const modal = document.getElementById('pepper-survey-modal');

        button.addEventListener('click', () => {
            modal.style.display = 'flex';
            // Force a reflow
            modal.offsetHeight;
            modal.classList.add('visible');
            document.body.style.overflow = 'hidden';
        });

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal();
            }
        });

        // Listen for messages from the iframe
        window.addEventListener('message', (event) => {
            if (event.origin === window.location.origin) {
                if (event.data.type === 'survey-submitted') {
                    this.closeModal();
                    if (this.config.onSubmit) {
                        this.config.onSubmit(event.data);
                    }
                }
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    closeModal() {
        const modal = document.getElementById('pepper-survey-modal');
        modal.classList.remove('visible');
        // Wait for the animation to complete before hiding the modal
        setTimeout(() => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }, parseFloat(this.config.animationDuration) * 1000);
    }
}

// Usage example:
/*
new PepperSurvey({
    formId: 'your-form-id',
    buttonText: 'Take Our Survey',
    buttonColor: '#1a73e8',
    buttonPosition: 'bottom-right',
    buttonIcon: '📋',
    modalWidth: '90%',
    modalMaxWidth: '800px',
    modalHeight: '80vh',
    animationDuration: '0.3s',
    theme: 'light',
    customStyles: {
        button: {
            // Custom button styles
        }
    },
    onSubmit: (data) => {
        console.log('Survey submitted:', data);
    }
});
*/ 