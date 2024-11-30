/*=============== SHOW MENU ===============*/
const navMenu = document.getElementById('nav-menu'),
      navToggle = document.getElementById('nav-toggle'),
      navClose = document.getElementById('nav-close')

/* Menu show */
if(navToggle){
    navToggle.addEventListener('click', () =>{
        navMenu.classList.add('show-menu')
    })
}

/* Menu hidden */
if(navClose){
    navClose.addEventListener('click', () =>{
        navMenu.classList.remove('show-menu')
    })
}

/*=============== REMOVE MENU MOBILE ===============*/
const navLink = document.querySelectorAll('.nav__link')

const linkAction = () =>{
    const navMenu = document.getElementById('nav-menu')
    // When we click on each nav__link, we remove the show-menu class
    navMenu.classList.remove('show-menu')
}
navLink.forEach(n => n.addEventListener('click', linkAction))

/*=============== SWIPER SHOE ===============*/
let swiperShoes = new Swiper('.home__swiper', {
    loop: true,
    spaceBetween: 32,
    grabCursor: true,
    effect: 'creative',
    creativeEffect: {
        prev: {
            translate: [-100, 0, -500],
            opacity: 0,
        },
        next: {
            translate: [100, 0, -500],
            opacity: 0,
        },
    },

    pagination: {
        el: '.swiper-pagination',
        clickable: true,
    },
})

/*=============== SHADOW HEADER ===============*/
const shadowHeader = () =>{
    const header = document.getElementById('header')
    // Add a class if the bottom offset is greater than 50 of the viewport
    this.scrollY >= 50 ? header.classList.add('shadow-header') 
                       : header.classList.remove('shadow-header')
}
window.addEventListener('scroll', shadowHeader)

/*=============== Show more button ===============*/
// JavaScript for "Show More/Less" functionality
const showMoreButton = document.getElementById('show-more');
const productGrid = document.getElementById('product-grid');
const productCards = Array.from(productGrid.children); // Get all product cards

// Initially hide all but the first 10 products
const initialCount = 10;
productCards.forEach((card, index) => {
  if (index >= initialCount) {
    card.style.display = 'none';
  }
});

// Toggle "Show More" and "Show Less"
let isShowingMore = false; // Tracks current state

showMoreButton.addEventListener('click', () => {
  if (!isShowingMore) {
    // Show all products
    productCards.forEach((card) => {
      card.style.display = 'block';
    });
    showMoreButton.textContent = 'Show Less'; // Update button text
    isShowingMore = true;
  } else {
    // Show only the initial products
    productCards.forEach((card, index) => {
      if (index >= initialCount) {
        card.style.display = 'none';
      }
    });
    showMoreButton.textContent = 'Show More'; // Update button text
    isShowingMore = false;
  }
});

/*=============== PRODUCT SIZE SELECT ===============*/
function updatePrice(form, productId) {
  const priceDisplay = document.getElementById(`price-${productId}`);
  const selectedOption = form.querySelector('select').selectedOptions[0];
  const selectedPrice = selectedOption.getAttribute('data-price');
  
  if (priceDisplay && selectedPrice) {
      priceDisplay.textContent = `$${parseFloat(selectedPrice).toFixed(2)}`;
  }
}

