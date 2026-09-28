module.exports = {
  content: [
    './products/templates/**/*.html',
    './accounts/templates/**/*.html',
    './services/templates/**/*.html',
    './templates/**/*.html',
    './static/js/**/*.js'
  ],
  theme: {
    extend: {
      colors: {
        'deep-green': '#1a3628',
        'sandy': '#f4ebd8',
        'gold-accent': '#d4af37',
        'input-bg': '#374151',
        'input-border': '#4B5563'
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Outfit', 'sans-serif']
      },
      boxShadow: {
        soft: '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
        lift: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)'
      }
    }
  }
};
