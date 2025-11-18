// Função para aplicar o tema do cookie ao carregar
        document.addEventListener('DOMContentLoaded', () => {
            const theme = document.cookie.split(';').find(item => item.trim().startsWith('theme='));
            const themeValue = theme ? theme.split('=')[1] : 'light';
            document.body.className = themeValue;
        });