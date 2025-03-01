// Делаем функции доступными глобально
window.createWheel = createWheel;

function createWheel() {
    const wheelContainer = document.createElement('div');
    wheelContainer.className = 'wheel-container';
    wheelContainer.innerHTML = `
        <div id="wheel-app">
            <img class="marker" src="marker.png" />
            <img class="wheel" src="wheel.png" />
            <img class="button" src="button.png" />
        </div>
    `;

    // Добавляем обработчики
    const wheel = wheelContainer.querySelector('.wheel');
    const startButton = wheelContainer.querySelector('.button');
    let deg = 0;

    startButton.addEventListener('click', () => {
        // Отключаем кнопку во время вращения
        startButton.style.pointerEvents = 'none';
        
        // Генерируем случайное число от 0 до 100
        const random = Math.random() * 100;
        let currentProbability = 0;
        let selectedPrize = null;
        
        // Выбираем приз на основе вероятности
        for (const prize of prizes) {
            currentProbability += prize.probability;
            if (random <= currentProbability) {
                selectedPrize = prize;
                break;
            }
        }

        // Вычисляем угол поворота (5-10 оборотов)
        deg = Math.floor(5000 + Math.random() * 5000);
        
        // Устанавливаем переход и вращаем колесо
        wheel.style.transition = 'all 10s ease-out';
        wheel.style.transform = `rotate(${deg}deg)`;
        
        // Добавляем размытие
        wheel.classList.add('blur');
    });

    wheel.addEventListener('transitionend', () => {
        // Убираем размытие
        wheel.classList.remove('blur');
        
        // Включаем кнопку
        startButton.style.pointerEvents = 'auto';
        
        // Убираем transition для мгновенного поворота
        wheel.style.transition = 'none';
        
        // Вычисляем актуальный угол
        const actualDeg = deg % 360;
        
        // Определяем выигрыш
        const prizeIndex = Math.floor((360 - actualDeg) / (360 / prizes.length));
        const selectedPrize = prizes[prizeIndex];

        // Показываем сообщение о выигрыше
        let message = '';
        switch(selectedPrize.type) {
            case 'nothing':
                message = 'К сожалению, вы ничего не выиграли. Попробуйте еще раз!';
                break;
            case 'discount':
                message = `Поздравляем! Вы выиграли скидку ${selectedPrize.amount}₽ при заказе от ${selectedPrize.minOrder}₽!`;
                break;
            case 'free':
                message = `Поздравляем! Вы выиграли бесплатный заказ на сумму до ${selectedPrize.maxAmount}₽!`;
                break;
        }
        showNotification(message);
        
        // Устанавливаем конечное положение
        wheel.style.transform = `rotate(${actualDeg}deg)`;
    });

    return wheelContainer;
}

function showNotification(message) {
    // Показываем сообщение о выигрыше
    // Реализация функции showNotification не предоставлена
}
