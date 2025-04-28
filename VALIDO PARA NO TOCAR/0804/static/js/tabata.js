class TabataTimer {
    constructor() {
        this.workTime = 20;
        this.restTime = 10;
        this.rounds = 8;
        this.warmup = 60;
        this.cooldown = 60;
        this.currentRound = 0;
        this.currentPhase = 'ready';
        this.timeLeft = 0;
        this.timer = null;
        this.isRunning = false;

        // Elementos DOM
        this.minutesDisplay = document.getElementById('minutes');
        this.secondsDisplay = document.getElementById('seconds');
        this.currentRoundDisplay = document.getElementById('current-round');
        this.currentPhaseDisplay = document.getElementById('current-phase');
        this.startButton = document.getElementById('start-btn');
        this.pauseButton = document.getElementById('pause-btn');
        this.resetButton = document.getElementById('reset-btn');

        // Inputs
        this.workTimeInput = document.getElementById('work-time');
        this.restTimeInput = document.getElementById('rest-time');
        this.roundsInput = document.getElementById('rounds');
        this.warmupInput = document.getElementById('warmup');
        this.cooldownInput = document.getElementById('cooldown');

        // Event listeners
        this.startButton.addEventListener('click', () => this.start());
        this.pauseButton.addEventListener('click', () => this.pause());
        this.resetButton.addEventListener('click', () => this.reset());

        // Sonidos
        this.workSound = new Audio('/static/sounds/work.mp3');
        this.restSound = new Audio('/static/sounds/rest.mp3');
        this.finishSound = new Audio('/static/sounds/finish.mp3');
    }

    updateDisplay() {
        const minutes = Math.floor(this.timeLeft / 60);
        const seconds = this.timeLeft % 60;
        this.minutesDisplay.textContent = minutes.toString().padStart(2, '0');
        this.secondsDisplay.textContent = seconds.toString().padStart(2, '0');
        this.currentRoundDisplay.textContent = `${this.currentRound}/${this.rounds}`;
        this.currentPhaseDisplay.textContent = this.currentPhase.charAt(0).toUpperCase() + this.currentPhase.slice(1);
    }

    start() {
        if (!this.isRunning) {
            this.isRunning = true;
            this.startButton.disabled = true;
            this.pauseButton.disabled = false;

            if (this.currentPhase === 'ready') {
                this.currentPhase = 'warmup';
                this.timeLeft = this.warmupInput.value;
                this.workSound.play();
            }

            this.timer = setInterval(() => {
                this.timeLeft--;
                this.updateDisplay();

                if (this.timeLeft <= 0) {
                    this.nextPhase();
                }
            }, 1000);
        }
    }

    pause() {
        if (this.isRunning) {
            this.isRunning = false;
            clearInterval(this.timer);
            this.startButton.disabled = false;
            this.pauseButton.disabled = true;
        }
    }

    reset() {
        this.pause();
        this.currentRound = 0;
        this.currentPhase = 'ready';
        this.timeLeft = 0;
        this.updateDisplay();
        this.startButton.disabled = false;
        this.pauseButton.disabled = true;
    }

    nextPhase() {
        clearInterval(this.timer);

        switch (this.currentPhase) {
            case 'warmup':
                this.currentPhase = 'work';
                this.currentRound = 1;
                this.timeLeft = this.workTimeInput.value;
                this.workSound.play();
                break;

            case 'work':
                if (this.currentRound < this.rounds) {
                    this.currentPhase = 'rest';
                    this.timeLeft = this.restTimeInput.value;
                    this.restSound.play();
                } else {
                    this.currentPhase = 'cooldown';
                    this.timeLeft = this.cooldownInput.value;
                    this.restSound.play();
                }
                break;

            case 'rest':
                this.currentPhase = 'work';
                this.currentRound++;
                this.timeLeft = this.workTimeInput.value;
                this.workSound.play();
                break;

            case 'cooldown':
                this.reset();
                this.finishSound.play();
                return;
        }

        this.updateDisplay();
        if (this.isRunning) {
            this.start();
        }
    }
}

// Inicializar el temporizador cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    new TabataTimer();
}); 