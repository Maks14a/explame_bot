// --- Настройки ---
// Замените эти значения на реальные данные вашего бэкенда
const API_BASE_URL = "http://127.0.0.1:8000";
const LOGING_SECRET = "v&DJGebnM-zWLgUp*Hc*CLxj2$KmW*qMypM4Hy)Gmneh8U8*)!!";
const BOT_USERNAME = "ТестБот"; // Например, "MyAwesomeLogBot"

/**
 * Функция для отправки лога ошибок на бэкенд.
 * @param {object} logDetails - Объект с деталями ошибки.
 * @param {string} logDetails.message - Сообщение об ошибке.
 * @param {string} [logDetails.url] - URL файла, где произошла ошибка.
 * @param {number} [logDetails.lineNumber] - Номер строки.
 * @param {number} [logDetails.columnNumber] - Номер столбца.
 * @param {string} [logDetails.stack] - Стек вызовов.
 */
async function sendLog(logDetails) {
    // Формируем полное сообщение для отправки
    const fullMessage = `
Сообщение: ${logDetails.message}
URL: ${logDetails.url || 'N/A'}
Строка: ${logDetails.lineNumber || 'N/A'}
Столбец: ${logDetails.columnNumber || 'N/A'}
Стек: ${logDetails.stack || 'N/A'}
    `;

    try {
        const response = await fetch(`${API_BASE_URL}/log`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${LOGING_SECRET}`
            },
            body: JSON.stringify({
                message: fullMessage,
                bot_username: BOT_USERNAME
            }),
        });

        if (response.ok) {
            console.log("Лог успешно отправлен!");
        } else {
            const errorData = await response.json();
            console.error(`Ошибка отправки лога: ${errorData.detail || 'Не удалось отправить лог.'}`);
        }
    } catch (error) {
        console.error("Сетевая ошибка при отправке лога:", error);
    }
}

// --- Перехват ошибок ---

// Перехватываем стандартные JavaScript-ошибки
window.onerror = function(message, url, lineNumber, columnNumber, error) {
    const logDetails = {
        message: message,
        url: url,
        lineNumber: lineNumber,
        columnNumber: columnNumber,
        stack: error ? error.stack : 'N/A'
    };
    sendLog(logDetails);
    // Возвращаем true, чтобы предотвратить стандартное отображение ошибки в консоли браузера
    return true; 
};

// Перехватываем неотработанные ошибки промисов (async/await, fetch и т.д.)
window.addEventListener('unhandledrejection', (event) => {
    const logDetails = {
        message: `Unhandled Promise Rejection: ${event.reason.message || event.reason}`,
        stack: event.reason.stack || 'N/A'
    };
    sendLog(logDetails);
    // Предотвращаем стандартное отображение ошибки в консоли
    event.preventDefault(); 
});

console.log("Система отправки логов активирована.");
