/**
 * ============================================
 * DAILY JOB - Jordan Job Posting Platform
 * Complete Production-Ready JavaScript (Fixed & Optimized)
 * ============================================
 */

(function () {
  "use strict";

  const BASE_URL = (window.location.protocol === 'file:') 
    ? "http://127.0.0.1:8000/api" 
    : "/api";

  const Api = {
    verifyEmail: async (email, otp) => {
      const res = await fetch(`${BASE_URL}/verify-email/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "الرمز غير صحيح");
      return data;
    },
    requestPasswordReset: async (email) => {
      const res = await fetch(`${BASE_URL}/password-reset/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      let data = {};
      try {
        data = await res.json();
      } catch (_) {
        throw new Error("تعذر الاتصال بخدمة استعادة كلمة المرور، يرجى المحاولة لاحقاً.");
      }
      if (!res.ok) throw new Error(data.error || "حدث خطأ أثناء الإرسال");
      return data;
    },
    confirmPasswordReset: async (email, otp, new_password) => {
      const res = await fetch(`${BASE_URL}/password-reset-confirm/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp, new_password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "الرابط غير صالح أو منتهي الصلاحية");
      return data;
    },
    login: async (email, password) => {
      const res = await fetch(`${BASE_URL}/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: email, password: password })
      });
      const data = await res.json();
      if (res.status === 403) throw new Error(data.error || "الحساب غير مفعّل. يرجى تأكيد بريدك الإلكتروني أولاً.");
      if (!res.ok) throw new Error(data.error || "بيانات الدخول غير صحيحة");
      return {
        token: data.token,
        user: { 
          id: data.user_id, 
          email: email, 
          username: data.username || email.split('@')[0],
          role: data.role || 'user'
        }
      };
    },
    register: async (email, username, password, referralCode = '') => {
      // Django's default username validator doesn't allow spaces. Replace with underscores.
      const safeUsername = username.replace(/\s+/g, '_');
      
      const payload = { email, username: safeUsername, password };
      if (referralCode) {
        payload.referred_by_code = referralCode.trim();
      }
      
      const res = await fetch(`${BASE_URL}/users/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      let data = {};
      try {
        data = await res.json();
      } catch (_) {
        throw new Error("حدث خطأ في استجابة الخادم، يرجى المحاولة لاحقاً.");
      }
      
      if (!res.ok) {
        let errorMsg = data.email?.[0] || data.username?.[0] || data.error || data.detail || "فشل في إنشاء الحساب، تحقق من البيانات.";
        
        // Translate common Django DRF errors
        if (state.lang === 'ar') {
          if (errorMsg.includes("username already exists")) errorMsg = "اسم المستخدم هذا مسجل مسبقاً.";
          else if (errorMsg.includes("email already exists")) errorMsg = "هذا البريد الإلكتروني مسجل مسبقاً.";
          else if (errorMsg.includes("valid username")) errorMsg = "اسم المستخدم يجب أن يحتوي على أحرف وأرقام فقط.";
        }
        
        throw new Error(errorMsg);
      }
      
      return data;
    },
    getAds: async (page = 1) => {
      const res = await fetch(`${BASE_URL}/ads/?page=${page}`);
      if (!res.ok) return { results: [], next: null };
      return await res.json();
    },
    getNotifications: async (token) => {
      const res = await fetch(`${BASE_URL}/notifications/`, {
        method: 'GET',
        headers: { 'Authorization': 'Token ' + token }
      });
      if (res.status === 401) { logout(); throw new Error('Session expired'); }
      if (!res.ok) return [];
      return await res.json();
    },
    deleteAd: async (adId, token) => {
      const res = await fetch(`${BASE_URL}/ads/${adId}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Token ${token}` }
      });
      if (res.status === 401) { logout(); throw new Error('Session expired'); }
      if (!res.ok) throw new Error("حدث خطأ أثناء حذف الإعلان.");
      return true;
    },
    deleteAccount: async (userId, token) => {
      // (إصلاح) التحقق من وجود userId قبل الإرسال
      if (!userId || userId === 'undefined' || userId === 'null') {
        throw new Error("معرّف المستخدم غير موجود. يرجى تسجيل الخروج وإعادة الدخول.");
      }
      const res = await fetch(`${BASE_URL}/users/${userId}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Token ${token}` }
      });
      if (res.status === 401) { logout(); throw new Error('Session expired'); }
      if (!res.ok) throw new Error("حدث خطأ أثناء حذف الحساب.");
      return true;
    },
    getCoupons: async (token) => {
      // (اقتراح #5) جلب القسائم من الـ API
      const res = await fetch(`${BASE_URL}/coupons/`, {
        headers: { 'Authorization': `Token ${token}` }
      });
      if (res.status === 401) { logout(); throw new Error('Session expired'); }
      if (!res.ok) return [];
      const data = await res.json();
      return data?.results ?? data ?? [];
    },
    resendOtp: async (email) => {
      const res = await fetch(`${BASE_URL}/resend-otp/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "فشل إعادة إرسال الرمز");
      return data;
    },
    markNotificationRead: async (notifId, token) => {
      // تعديل 4: حفظ حالة القراءة في السيرفر
      try {
        await fetch(`${BASE_URL}/notifications/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Token ' + token },
          body: JSON.stringify({ id: notifId })
        });
      } catch (e) { /* silent fail */ }
    },
    markAllNotificationsRead: async (token) => {
      // تعديل 4: تعليم كل الإشعارات مقروءة في السيرفر
      try {
        await fetch(`${BASE_URL}/notifications/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Token ' + token },
          body: JSON.stringify({ mark_all: true })
        });
      } catch (e) { /* silent fail */ }
    },
    deleteNotifications: async (ids, token) => {
      try {
        const body = (ids === 'all' || !ids) ? { delete_all: true } : { ids: Array.isArray(ids) ? ids : [ids] };
        const res = await fetch(`${BASE_URL}/notifications/`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Token ' + token },
          body: JSON.stringify(body)
        });
        return res.ok;
      } catch (e) {
        return false;
      }
    },
    getAdsSilent: async (page = 1) => {
      // تعديل 3: جلب صامت للإعلانات بدون throwing
      try {
        const res = await fetch(`${BASE_URL}/ads/?page=${page}`);
        if (!res.ok) return null;
        return await res.json();
      } catch (e) {
        return null;
      }
    },
    getAd: async (id) => {
      const token = localStorage.getItem("dj_token");
      const headers = token ? { 'Authorization': `Token ${token}` } : {};
      const res = await fetch(`${BASE_URL}/ads/${id}/`, { headers });
      if (res.status === 401 && token) { logout(); throw new Error('Session expired'); }
      if (!res.ok) throw new Error("الإعلان غير متوفر أو تم حذفه");
      return await res.json();
    }
  };


  const GOVERNORATES = [
    { key: "amman", ar: "عمّان", en: "Amman" },
    { key: "zarqa", ar: "الزرقاء", en: "Zarqa" },
    { key: "irbid", ar: "إربد", en: "Irbid" },
    { key: "balqa", ar: "البلقاء", en: "Balqa" },
    { key: "madaba", ar: "مادبا", en: "Madaba" },
    { key: "karak", ar: "الكرك", en: "Karak" },
    { key: "tafilah", ar: "الطفيلة", en: "Tafilah" },
    { key: "maan", ar: "معان", en: "Ma'an" },
    { key: "aqaba", ar: "العقبة", en: "Aqaba" },
    { key: "jerash", ar: "جرش", en: "Jerash" },
    { key: "ajloun", ar: "عجلون", en: "Ajloun" },
    { key: "mafraq", ar: "المفرق", en: "Mafraq" }
  ];

  const GOV_MAP = Object.fromEntries(GOVERNORATES.map((g) => [g.key, g]));

  const CATEGORIES = [
    { key: "daily", ar: "عمل يومي", en: "Daily Jobs", icon: "fa-bolt", color: "#FF6A00" },
    { key: "fulltime", ar: "وظائف دوام كامل", en: "Full-Time Jobs", icon: "fa-briefcase", color: "#1967D2" },
    { key: "ads", ar: "إعلانات وأخبار", en: "Ads & News", icon: "fa-rectangle-ad", color: "#C2185B" },
    { key: "services", ar: "خدمات", en: "Services", icon: "fa-hand-holding-hand", color: "#1565C0" },
    { key: "used", ar: "أشياء مستعملة", en: "Used Items", icon: "fa-comment-dots", color: "#546E7A" },
    { key: "free", ar: "هدايا مجانية", en: "Freebies", icon: "fa-gift", color: "#2E7D32" },
    { key: "real_estate", ar: "عقارات", en: "Real Estate", icon: "fa-building", color: "#6A1B9A" },
    { key: "rentals", ar: "إيجار", en: "Rentals", icon: "fa-key", color: "#00838F" },
    { key: "cars", ar: "سيارات", en: "Cars", icon: "fa-car", color: "#E65100" },
    { key: "construction", ar: "أعمال بناء", en: "Construction & Building", parent: "services" },
    { key: "delivery", ar: "توصيل", en: "Delivery & Courier", parent: "services" },
    { key: "cleaning", ar: "نظافة", en: "Housekeeping & Cleaning", parent: "services" },
    { key: "moving", ar: "نقل وأثاث", en: "Moving & Packing", parent: "services" },
    { key: "plumbing", ar: "سباكة وتدفئة", en: "Plumbing & Heating", parent: "services" },
    { key: "electrical", ar: "كهرباء", en: "Electrical Work", parent: "services" },
    { key: "hospitality", ar: "ضيافة ومطاعم", en: "Restaurants & Catering", parent: "services" },
    { key: "caregiving", ar: "رعاية أطفال", en: "Babysitting & Care", parent: "services" },
    { key: "electronics", ar: "إلكترونيات مستعملة", en: "Used Electronics", parent: "used" },
    { key: "furniture", ar: "أثاث مستعمل", en: "Used Furniture", parent: "used" },
    { key: "other", ar: "أخرى", en: "Other" }
  ];

  const CAT_MAP = Object.fromEntries(CATEGORIES.map((c) => [c.key, c]));

  function getMainCategory(key) {
    const cat = CAT_MAP[key];
    return cat?.parent || cat?.key || key;
  }

  function getCategoryName(key, lang) {
    const cat = CAT_MAP[key];
    if (!cat) return key;
    return cat[lang] || cat.en;
  }

  const i18n = {
    en: {
      contactUs: "Contact Us",
      contactName: "Name",
      contactEmail: "Email",
      contactSubject: "Subject",
      contactMessage: "Message",
      send: "Send",

      forgotPassword: "Forgot Password?",
      cliqAccount: "CliQ Account - Dinarak Wallet (Alias: DAILYJOB1)",
      cliqTransferMsg: "Please transfer 1 JOD to CliQ Account - Dinarak Wallet (Alias: <strong>DAILYJOB1</strong>) and upload the receipt below:",
      uploadReceipt: "Upload Receipt",
      confirmPaymentAndPublish: "Confirm Payment & Publish",
      receiptRequired: "Please upload the payment receipt",
      postAd: "Post Your Ad Now",
      all: "All",
      dailyJob: "Daily Jobs",
      fullTime: "Full-Time Jobs",
      announcements: "Ads & News",
      services: "Services",
      usedGoods: "Used Items",
      freebies: "Freebies",
      realEstate: "Real Estate",
      rentals: "Rentals",
      cars: "Cars",
      activeAds: "Active Listings",
      noResults: "No results match your search",
      adDetails: "Ad Details",
      jobDesc: "Description",
      contactWhatsapp: "Call or WhatsApp",
      abuDinar: "Abu Al-Dinar",
      abuDinarSub: "Best way to connect your service with employers and users",
      adTitle: "Ad Title",
      governorate: "Governorate",
      category: "Category",
      dailyWage: "Daily Wage / Price (JOD)",
      details: "Details",
      contactMethod: "Contact Method",
      phoneNumber: "Phone Number",
      postingFee: "Posting Fee",
      free: "Free",
      reviewFee: "Review Fee",
      total: "Total",
      publishAd: "Publish Ad - 1 JOD",
      favorites: "Favorites",
      noFavorites: "You haven't added any favorites yet",
      myAds: "My Listings",
      noAdsYet: "You haven't posted any ads yet",
      postFirstAd: "Post Your First Ad",
      notifications: "Notifications",
      markAllRead: "Mark All as Read",
      deleteAll: "Delete All",
      confirmDeleteAllNotifs: "Are you sure you want to delete all notifications?",
      confirmDeleteNotif: "Are you sure you want to delete this notification?",
      allNotifsDeleted: "All notifications deleted",
      notifDeleted: "Notification deleted",
      views: "Views",
      viewsCount: "views",
      noNotifications: "No notifications at the moment",
      settings: "Settings",
      accountInfo: "Account Information",
      email: "Email Address",
      username: "Username",
      saveChanges: "Save Changes",
      notificationPrefs: "Notification Preferences",
      generalNotifs: "General Notifications",
      generalNotifsDesc: "Alerts about your account activity",
      newMessages: "New Messages",
      newMessagesDesc: "When you receive a message from a user",
      offersNews: "Offers & News",
      offersNewsDesc: "Offers and updates from Daily Job",
      preferredGov: "Preferred Governorate",
      chooseGovDefault: "Choose default governorate for displaying ads",
      deleteAccount: "Delete Account Permanently",
      confirmDeleteAd: "Are you sure you want to delete this ad permanently?",
      confirmDeleteAccount: "Are you sure you want to delete your account permanently? This action cannot be undone.",
      language: "Language",
      directionHint: "Direction changes automatically (LTR/RTL)",
      accountActions: "Account Actions",
      logout: "Log Out",
      home: "Home",
      favorites: "Favorites",
      myAds: "My Listings",
      myCoupons: "My Coupons",
      settings: "Settings",
      login: "Login",
      register: "Register",
      loginSub: "Enter your email and password to continue",
      password: "Password",
      createAccount: "Create Account",
      registerSub: "Create your account in seconds - we only need these fields",
      confirmPassword: "Confirm Password",
      filterResults: "Filter Results",
      reset: "Reset",
      apply: "Apply",
      abuDinarCta: "Abu Al-Dinar - Post Ad",
      searchPlaceholder: "Search for jobs or used items...",
      showAllAds: "Show All Ads",
      loadMoreAds: "Load More Ads",
      loading: "Loading...",
      minsAgo: "minutes ago",
      hoursAgo: "hours ago",
      daysAgo: "days ago",
      loginSuccess: "Logged in successfully",
      registerSuccess: "Account created successfully",
      logoutSuccess: "Logged out successfully",
      adPublished: "Thank you, your ad will be published after 10 minutes",
      settingsSaved: "Settings saved successfully",
      fillAllFields: "Please fill in all fields",
      passwordsMismatch: "Passwords do not match",
      invalidEmail: "Invalid email address",
      invalidPhone: "Phone must start with 07 and be 10 digits (e.g. 07XXXXXXXX)",
      titleRequired: "Title is required",
      wageRequired: "Wage is required",
      phoneRequired: "Phone number is required",
      contact: "Contact",
      myAd: "My Ad",
      removedFromFav: "Removed from favorites",
      addedToFav: "Added to favorites",
      filtersApplied: "Filters applied",
      filtersReset: "Filters reset",
      allMarkedRead: "All marked as read",
      sharingNotSupported: "Sharing not supported on this device",
      preferredGovUpdated: "Preferred governorate updated",
      couponsOffers: "Coupons & Offers",
      referralDesc: "For every friend who registers on the app using your referral code and activates their account, you will automatically receive a free ad coupon valid for 30 days!",
      yourReferralCode: "Your Referral Code is",
      copyBtn: "Copy",
      shareReferralBtn: "Share Referral Code with Friends",
      activeCoupons: "Your Active Coupons",
      noActiveCoupons: "No active coupons currently. Share your referral code with friends to get new coupons!",
      couponsHistory: "Coupons History",
      couponsHistoryEmpty: "Coupons history is empty.",
      referralCode: "Referral Code (Optional)",
      shareMsg: "Register on the Daily Job app to search for daily jobs or post your ads for free! Use my referral code: {code} when registering to get a welcome gift!",
      shareSuccessToast: "Share message copied successfully!",
      usernameMinLength: "Username must be at least 3 characters",
      passwordMinLength: "Password must be at least 6 characters",
      guest: "Guest",
      signInToSeeMore: "Sign in to see more",
      whatsapp: "WhatsApp",
      call: "Phone Call",
      both: "Call or WhatsApp"
    },
    ar: {
      contactUs: "اتصل بنا",
      contactName: "الاسم",
      contactEmail: "البريد الإلكتروني",
      contactSubject: "الموضوع",
      contactMessage: "الرسالة",
      send: "إرسال",

      forgotPassword: "نسيت كلمة المرور؟",
      cliqAccount: "حساب كليك - محفظة دينارك (اسم مستعار: DAILYJOB1)",
      cliqTransferMsg: "يرجى تحويل 1 دينار إلى حساب كليك - محفظة دينارك (اسم مستعار: DAILYJOB1) وتحميل صورة الإيصال أدناه:",
      uploadReceipt: "تحميل الإيصال",
      confirmPaymentAndPublish: "تأكيد الدفع والنشر",
      receiptRequired: "الرجاء رفع صورة إيصال الدفع",
      postAd: "أنشر إعلانك الآن",
      all: "الكل",
      dailyJob: "شغل يومي",
      fullTime: "وظائف دوام كامل",
      announcements: "إعلانات وأخبار",
      services: "خدمات",
      usedGoods: "أغراض مستعملة",
      freebies: "هدايا مجانية",
      realEstate: "عقارات",
      rentals: "إيجار",
      cars: "سيارات",
      activeAds: "إعلانات نشطة",
      noResults: "لا توجد نتائج مطابقة لبحثك",
      adDetails: "تفاصيل الإعلان",
      jobDesc: "وصف العمل",
      contactWhatsapp: "اتصال أو واتساب",
      abuDinar: "أبو الدينار",
      abuDinarSub: "أفضل طريقة لتوصيل خدمتك بالمعلن والمستخدم",
      adTitle: "عنوان الإعلان",
      governorate: "المحافظة",
      category: "الفئة",
      dailyWage: "الأجر اليومي / السعر (د.أ)",
      details: "التفاصيل",
      contactMethod: "طريقة التواصل المباشر",
      phoneNumber: "رقم التواصل",
      postingFee: "رسوم نشر الإعلان",
      free: "مجانية",
      reviewFee: "مراجعة الإعلان",
      total: "المجموع",
      publishAd: "انشر الإعلان - 1 دينار",
      favorites: "المفضلة",
      noFavorites: "لم تضف أي إعلان للمفضلة بعد",
      myAds: "إعلاناتي",
      noAdsYet: "لم تنشر أي إعلان بعد",
      postFirstAd: "انشر أول إعلان",
      notifications: "الإشعارات",
      markAllRead: "تعليم الكل كمقروء",
      deleteAll: "حذف الكل",
      confirmDeleteAllNotifs: "هل أنت متأكد من حذف جميع الإشعارات؟",
      confirmDeleteNotif: "هل أنت متأكد من حذف هذا الإشعار؟",
      allNotifsDeleted: "تم حذف جميع الإشعارات بنجاح",
      notifDeleted: "تم حذف الإشعار بنجاح",
      views: "المشاهدات",
      viewsCount: "مشاهدة",
      noNotifications: "لا توجد إشعارات حالياً",
      settings: "الإعدادات",
      accountInfo: "معلومات الحساب",
      email: "البريد الإلكتروني",
      username: "اسم المستخدم",
      saveChanges: "حفظ التغييرات",
      notificationPrefs: "تفضيلات الإشعارات",
      generalNotifs: "إشعارات عامة",
      generalNotifsDesc: "تنبيهات حول نشاط حسابك",
      newMessages: "رسائل جديدة",
      newMessagesDesc: "عندما تتلقى رسالة من مستخدم",
      offersNews: "العروض والأخبار",
      offersNewsDesc: "العروض والتحديثات من دايلي جوب",
      preferredGov: "المحافظة المفضلة",
      chooseGovDefault: "اختر المحافظة الافتراضية لعرض الإعلانات",
      deleteAccount: "حذف الحساب نهائياً",
      confirmDeleteAd: "هل أنت متأكد أنك تريد حذف هذا الإعلان نهائياً؟",
      confirmDeleteAccount: "هل أنت متأكد من حذف حسابك نهائياً؟ لا يمكن التراجع عن هذا الإجراء وسيتم حذف جميع إعلاناتك.",
      language: "اللغة",
      directionHint: "يتغير الاتجاه تلقائياً (RTL/LTR)",
      accountActions: "إجراءات الحساب",
      logout: "تسجيل الخروج",
      home: "الرئيسية",
      favorites: "المفضلة",
      myAds: "إعلاناتي",
      myCoupons: "قسائمي",
      settings: "الإعدادات",
      login: "تسجيل الدخول",
      register: "إنشاء حساب",
      loginSub: "أدخل بريدك الإلكتروني وكلمة المرور للمتابعة",
      password: "كلمة المرور",
      createAccount: "إنشاء حساب جديد",
      registerSub: "أنشئ حسابك خلال ثوانٍ - نحتاج هذه الحقول فقط",
      confirmPassword: "تأكيد كلمة المرور",
      filterResults: "تصفية النتائج",
      reset: "إعادة تعيين",
      apply: "تطبيق",
      abuDinarCta: "أبو الدينار - أضف إعلان",
      searchPlaceholder: "ابحث عن شغلة عامل أو عرض مستعمل...",
      minsAgo: "دقيقة مضت",
      hoursAgo: "ساعة مضت",
      daysAgo: "أيام مضت",
      loginSuccess: "تم تسجيل الدخول بنجاح",
      registerSuccess: "تم إنشاء الحساب بنجاح",
      logoutSuccess: "تم تسجيل الخروج",
      adPublished: "شكراً، سيتم نشر الإعلان بعد 10 دقائق",
      settingsSaved: "تم حفظ الإعدادات",
      fillAllFields: "الرجاء تعبئة جميع الحقول",
      passwordsMismatch: "كلمتا المرور غير متطابقتين",
      invalidEmail: "البريد الإلكتروني غير صالح",
      invalidPhone: "رقم الهاتف يجب أن يبدأ بـ 07 ويتكون من 10 أرقام (مثال: 07XXXXXXXX)",
      titleRequired: "العنوان مطلوب",
      wageRequired: "الأجر مطلوب",
      phoneRequired: "رقم التواصل مطلوب",
      contact: "تواصل",
      myAd: "إعلاني",
      removedFromFav: "تم الإزالة من المفضلة",
      addedToFav: "تمت الإضافة إلى المفضلة",
      filtersApplied: "تم تطبيق الفلاتر",
      filtersReset: "تم إعادة تعيين الفلاتر",
      allMarkedRead: "تم تعليم الكل كمقروء",
      sharingNotSupported: "المشاركة غير مدعومة على هذا الجهاز",
      preferredGovUpdated: "تم تحديث المحافظة المفضلة",
      couponsOffers: "القسائم والعروض",
      referralDesc: "لكل صديق يسجل في التطبيق عن طريق كود الإحالة الخاص بك ويقوم بتفعيل حسابه، ستحصل تلقائياً على قسيمة إعلان مجاني صالحة لمدة 30 يوماً!",
      yourReferralCode: "كود الإحالة الخاص بك هو",
      copyBtn: "نسخ",
      shareReferralBtn: "مشاركة كود الإحالة مع الأصدقاء",
      activeCoupons: "قسائمك النشطة",
      noActiveCoupons: "لا توجد قسائم نشطة حالياً. شارك كود الإحالة مع أصدقائك للحصول على قسائم جديدة!",
      couponsHistory: "سجل القسائم",
      couponsHistoryEmpty: "سجل القسائم فارغ.",
      referralCode: "كود الإحالة (اختياري)",
      shareMsg: "سجل في تطبيق Daily Job وابحث عن وظائف يومية أو انشر إعلاناتك مجاناً! استخدم كود الإحالة الخاص بي: {code} عند التسجيل للحصول على هدية ترحيبية!",
      shareSuccessToast: "تم نسخ رسالة المشاركة بنجاح!",
      usernameMinLength: "يجب أن يكون اسم المستخدم 3 أحرف على الأقل",
      passwordMinLength: "يجب أن تكون كلمة المرور 6 أحرف على الأقل",
      guest: "زائر",
      signInToSeeMore: "سجّل دخولك لرؤية المزيد",
      whatsapp: "واتساب",
      call: "اتصال",
      both: "اتصال أو واتساب",
      showAllAds: "عرض كل الإعلانات",
      loadMoreAds: "تحميل المزيد من الإعلانات",
      loading: "جاري التحميل..."
    }
  };

  const state = {
    lang: localStorage.getItem("dj_lang") || "ar",
    isAuthenticated: false,
    user: null,
    pendingAction: null,
    favorites: new Set(JSON.parse(localStorage.getItem("dj_favorites") || "[]")),
    filters: {
      type: "all",
      category: "all",
      governorate: "all",
      query: ""
    },
    currentAdId: null,
    currentEditAdId: null,
    notifications: [],
    settings: {
      pushNotifications: true,
      messageNotifications: true,
      marketingNotifications: false,
      preferredGovernorate: "all"
    },
    tempEmail: sessionStorage.getItem('dj_tempEmail') || null,
    tempPassword: sessionStorage.getItem('dj_tempPassword') || null,
    resetUserEmail: ''
  };

  let ads = [];
  let currentAdsPage = 1;
  let hasMoreAds = false;

  function mapDbAd(dbAd) {
    return {
      id: dbAd.id,
      type: dbAd.category,
      category: dbAd.category,
      governorate: dbAd.governorate,
      area: { ar: dbAd.governorate, en: dbAd.governorate },
      title: { ar: dbAd.title, en: dbAd.title },
      desc: { ar: dbAd.description, en: dbAd.description },
      price: parseFloat(dbAd.price) || 0,
      currency: "JOD",
      wageType: "fixed",
      phone: dbAd.contact_phone,
      contactMethod: dbAd.contact_method || "both",
      createdAt: new Date(dbAd.created_at),
      user_email: dbAd.user_details?.email,
      mine: !!(state.user && (dbAd.user === state.user.id || dbAd.user_details?.username === state.user.username)),
      image: dbAd.image ? dbAd.image : 'https://placehold.co/400x300/e9ecef/495057?text=Daily+Job',
      extra_images: dbAd.extra_images || [],
      status: dbAd.status || 'approved',
      views: dbAd.views || 0
    };
  }

  async function loadAdsFromAPI(page = 1, append = false) {
    try {
      if (!append) {
        currentAdsPage = 1;
      }
      
      const dbResponse = await Api.getAds(page);
      const dbAds = dbResponse.results ? dbResponse.results : (Array.isArray(dbResponse) ? dbResponse : []);
      hasMoreAds = !!dbResponse.next;
      
      const newAds = dbAds.map(mapDbAd);
      
      if (append) {
        ads = [...ads, ...newAds];
      } else {
        ads = newAds;
        try {
          localStorage.setItem("dj_cached_ads", JSON.stringify(newAds));
        } catch (e) {}
      }
      renderAds();
      
      const loadMoreBtn = document.getElementById("loadMoreAdsBtn");
      if (loadMoreBtn) {
        loadMoreBtn.style.display = hasMoreAds ? "block" : "none";
      }
    } catch (e) {
      console.error("Failed to load ads", e);
    }
  }

  window.loadMoreAds = function() {
    if (hasMoreAds) {
      const loadMoreBtn = document.getElementById("loadMoreAdsBtn");
      const loadingText = (i18n[state.lang] && i18n[state.lang].loading) || "Loading...";
      const normalText = (i18n[state.lang] && i18n[state.lang].loadMoreAds) || "Load More Ads";
      if (loadMoreBtn) loadMoreBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${loadingText}`;
      
      currentAdsPage++;
      loadAdsFromAPI(currentAdsPage, true).then(() => {
        if (loadMoreBtn) loadMoreBtn.textContent = normalText;
      });
    }
  };

  // تعديل 3: Background polling - تحديث صامت كل 45 ثانية
  let _pollingInterval = null;
  function startSilentPolling() {
    if (_pollingInterval) return; // تجنب التكرار
    _pollingInterval = setInterval(async () => {
      // توفير موارد السيرفر وبيانات المستخدم إذا كان التبويب مصغراً أو في الخلفية
      if (document.hidden) return;

      // لا نحدث إذا كان المستخدم في منتصف نموذج أو شاشة تفاصيل
      const activeScreen = document.querySelector('.screen.active, .screen[style*="display: block"]');
      const activeScreenId = activeScreen?.id || '';
      if (['screen-add', 'screen-edit', 'screen-details'].includes(activeScreenId)) return;

      const freshData = await Api.getAdsSilent(1);
      if (!freshData || !freshData.results) return;

      const freshIds = new Set(freshData.results.map(a => a.id));
      const currentIds = new Set(ads.map(a => a.id));

      // هل هناك إعلانات جديدة أو محذوفة؟
      const hasChanges = freshData.results.some(a => !currentIds.has(a.id)) ||
                         ads.some(a => a.status === 'approved' && !freshIds.has(a.id));

      if (hasChanges) {
        // تحديث صامت: دمج الجديد مع الموجود بدون إعادة رسم كاملة
        const newMapped = freshData.results.map(mapDbAd);

        // الاحتفاظ بالصفحات الإضافية المحملة وإضافة الجديدة في البداية
        const page2PlusAds = ads.filter(a => !currentIds.has(a.id) || 
          !freshData.results.find(f => f.id === a.id));
        ads = [...newMapped, ...page2PlusAds.filter(a => !freshIds.has(a.id))];
        try {
          localStorage.setItem("dj_cached_ads", JSON.stringify(ads.slice(0, 50)));
        } catch (e) {}
        renderAds();
      }

      // تحديث صامت للإشعارات كذلك
      if (state.isAuthenticated) {
        const token = localStorage.getItem("dj_token");
        if (token) {
          try {
            const notifData = await Api.getNotifications(token);
            state.notifications = notifData;
            updateNotificationDot();
          } catch(e) { /* silent */ }
        }
      }
    }, 45000); // كل 45 ثانية
  }

  function stopSilentPolling() {
    if (_pollingInterval) {
      clearInterval(_pollingInterval);
      _pollingInterval = null;
    }
  }

  async function fetchNotifications() {
    const token = localStorage.getItem("dj_token");
    if (state.isAuthenticated && token) {
      try {
        const data = await Api.getNotifications(token);
        state.notifications = data;
        try {
          localStorage.setItem("dj_cached_notifications", JSON.stringify(data));
        } catch(e) {}
        renderNotifications();
        updateNotificationDot();
      } catch (e) {
        console.error("Failed to fetch notifications", e);
      }
    }
  }

  function minsAgo(n) {
    return new Date(Date.now() - n * 60000);
  }

  const elements = {
    authOverlay: document.getElementById("authOverlay"),
    authStepLogin: document.getElementById("authStepLogin"),
    authStepRegister: document.getElementById("authStepRegister"),
    drawerOverlay: document.getElementById("drawerOverlay"),
    filterOverlay: document.getElementById("filterOverlay"),
    cliqModalOverlay: document.getElementById("cliqModalOverlay"),
    toast: document.getElementById("toast")
  };

  function closeCliqModal() {
    if (elements.cliqModalOverlay) elements.cliqModalOverlay.classList.remove("open");
  }

  const cliqCloseBtn = document.getElementById("cliqModalClose");
  if (cliqCloseBtn) cliqCloseBtn.addEventListener("click", closeCliqModal);
  if (elements.cliqModalOverlay) {
    elements.cliqModalOverlay.addEventListener("click", (e) => {
      if (e.target === elements.cliqModalOverlay) closeCliqModal();
    });
  }

  function showAuthStep(stepId) {
    document.querySelectorAll('.auth-step').forEach(s => {
      s.classList.add('hidden');
    });
    
    const target = document.getElementById(stepId);
    if (target) {
      target.classList.remove('hidden');
    }

    const tLogin = document.getElementById("tabLogin");
    const tReg = document.getElementById("tabRegister");
    if (tLogin && tReg) {
      if (stepId === 'authStepLogin') {
        tLogin.classList.add("active");
        tReg.classList.remove("active");
      } else if (stepId === 'authStepRegister') {
        tReg.classList.add("active");
        tLogin.classList.remove("active");
      }
    }
  }

  function showLoginStep() { showAuthStep('authStepLogin'); }
  function showRegisterStep() { showAuthStep('authStepRegister'); }

  function openAuth(mode) {
    if (mode === "register") showRegisterStep();
    else showLoginStep();
    
    const lErr = document.getElementById("loginError");
    const rErr = document.getElementById("registerError");
    if (lErr) lErr.classList.add("hidden");
    if (rErr) rErr.classList.add("hidden");
    if (elements.authOverlay) elements.authOverlay.classList.add("open");
  }

  function closeAuth() {
    if (elements.authOverlay) elements.authOverlay.classList.remove("open");
  }

  const loginSubmitBtn = document.getElementById("loginSubmitBtn");
  if (loginSubmitBtn) {
    loginSubmitBtn.addEventListener("click", async () => {
      const emailEl = document.getElementById("loginEmail");
      const passEl = document.getElementById("loginPassword");
      const errorEl = document.getElementById("loginError");

      if (!emailEl || !passEl) return;
      const email = emailEl.value.trim();
      const password = passEl.value;

      if (!email || !password) {
        showFormError(errorEl, t("fillAllFields"));
        return;
      }

      if (!isValidEmail(email)) {
        showFormError(errorEl, t("invalidEmail"));
        return;
      }

      const originalText = loginSubmitBtn.innerHTML;
      try {
        loginSubmitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Loading...</span>';
        loginSubmitBtn.disabled = true;

        const result = await Api.login(email, password);

        state.isAuthenticated = true;
        state.user = result.user;

        localStorage.setItem("dj_user", JSON.stringify(state.user));
        localStorage.setItem("dj_token", result.token);

        closeAuth();
        updateDrawerUser();
        showToast(t("loginSuccess"), "success");
      
        loadAdsFromAPI();
        fetchNotifications();

        if (typeof state.pendingAction === "function") {
          const fn = state.pendingAction;
          state.pendingAction = null;
          fn();
        }

      } catch (error) {
        if (error.message.includes("الحساب غير مفعّل")) {
          errorEl.innerHTML = `${error.message} <br><a href="#" id="resendOtpLoginBtn" style="color:#FF6A00; text-decoration:underline; font-weight:bold;">إرسال رمز التفعيل مجدداً</a>`;
          errorEl.classList.remove("hidden");
          setTimeout(() => {
            const resendBtn = document.getElementById("resendOtpLoginBtn");
            if (resendBtn) {
              resendBtn.addEventListener("click", async (e) => {
                e.preventDefault();
                try {
                  resendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
                  await Api.resendOtp(email);
                  state.tempEmail = email;
                  state.tempPassword = password;
                  sessionStorage.setItem('dj_tempEmail', email);
                  sessionStorage.setItem('dj_tempPassword', password);
                  showToast("تم إرسال رمز التفعيل لبريدك!", "success");
                  document.querySelectorAll('.auth-step').forEach(s => s.classList.add('hidden'));
                  document.getElementById('authStepVerify').classList.remove('hidden');
                } catch(err) {
                  showToast(err.message, "error");
                  resendBtn.innerHTML = 'إرسال رمز التفعيل مجدداً';
                }
              });
            }
          }, 0);
        } else {
          showFormError(errorEl, error.message || "Login failed. Please try again.");
        }
      } finally {
        loginSubmitBtn.innerHTML = originalText;
        loginSubmitBtn.disabled = false;
      }
    });
  }

  const registerSubmitBtn = document.getElementById("registerSubmitBtn");
  if (registerSubmitBtn) {
    registerSubmitBtn.addEventListener("click", async () => {
      const emailEl = document.getElementById("regEmail");
      const userEl = document.getElementById("regUsername");
      const passEl = document.getElementById("regPassword");
      const confEl = document.getElementById("regConfirm");
      const refEl = document.getElementById("regReferral");
      const errorEl = document.getElementById("registerError");

      if (!emailEl || !userEl || !passEl || !confEl) return;
      const email = emailEl.value.trim();
      const username = userEl.value.trim();
      const password = passEl.value;
      const confirm = confEl.value;
      const referralCode = refEl ? refEl.value.trim() : '';

      if (!email || !username || !password || !confirm) {
        showFormError(errorEl, t("fillAllFields"));
        return;
      }

      if (!isValidEmail(email)) {
        showFormError(errorEl, t("invalidEmail"));
        return;
      }

      if (username.length < 3) {
        showFormError(errorEl, t("usernameMinLength"));
        return;
      }

      if (password.length < 6) {
        showFormError(errorEl, t("passwordMinLength"));
        return;
      }

      if (password !== confirm) {
        showFormError(errorEl, t("passwordsMismatch"));
        return;
      }

      const originalText = registerSubmitBtn.innerHTML;
      try {
        registerSubmitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>جاري الإنشاء...</span>';
        registerSubmitBtn.disabled = true;

        const regRes = await Api.register(email, username, password, referralCode);
        
        if (regRes && regRes.auto_verified && regRes.token) {
          state.isAuthenticated = true;
          state.user = {
            id: regRes.user_id,
            email: regRes.email || email,
            username: regRes.username || username,
            role: regRes.role || 'user',
            referral_code: regRes.referral_code
          };
          localStorage.setItem("dj_user", JSON.stringify(state.user));
          localStorage.setItem("dj_token", regRes.token);
          closeAuth();
          updateDrawerUser();
          showToast(regRes.message || "تم إنشاء الحساب بنجاح! مرحباً بك 🎉", "success");
          fetchNotifications();
          return;
        }

        state.tempEmail = email;
        state.tempPassword = password;
        sessionStorage.setItem('dj_tempEmail', email);
        sessionStorage.setItem('dj_tempPassword', password);

        showToast("تم إرسال رمز التأكيد لبريدك!", "success");
        
        document.querySelectorAll('.auth-step').forEach(s => s.classList.add('hidden'));
        document.getElementById('authStepVerify').classList.remove('hidden');

      } catch (error) {
        showFormError(errorEl, error.message || "Registration failed. Please try again.");
      } finally {
        registerSubmitBtn.innerHTML = originalText;
        registerSubmitBtn.disabled = false;
      }
    });
  }

  function logout() {
    localStorage.removeItem("dj_user");
    localStorage.removeItem("dj_token");
    localStorage.removeItem("dj_favorites");
    localStorage.removeItem("dj_cached_notifications");
    
    state.isAuthenticated = false;
    state.user = null;
    state.favorites = new Set();
    
    updateDrawerUser();
    showToast(t("logoutSuccess"), "success");
    loadAdsFromAPI();
    goToScreen("home");
    closeDrawer();
  }

  const tLogin = document.getElementById("tabLogin");
  const tReg = document.getElementById("tabRegister");
  const authClose = document.getElementById("authClose");

  if (tLogin) tLogin.addEventListener("click", showLoginStep);
  if (tReg) tReg.addEventListener("click", showRegisterStep);
  if (authClose) authClose.addEventListener("click", closeAuth);
  if (elements.authOverlay) {
    elements.authOverlay.addEventListener("click", (e) => {
      if (e.target === elements.authOverlay) closeAuth();
    });
  }

  function goToScreen(name, pushState = true) {
    document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
    
    const targetScreen = document.getElementById("screen-" + name);
    if (targetScreen) targetScreen.classList.add("active");

    // حفظ الشاشة الحالية في sessionStorage لكي لا تضيع عند التحديث
    sessionStorage.setItem("dj_lastScreen", name);
    if (name === "details" && state.currentAdId) {
      sessionStorage.setItem("dj_lastAdId", state.currentAdId);
    } else if (name === "add") {
      if (state.currentEditAdId) {
        sessionStorage.setItem("dj_lastEditAdId", state.currentEditAdId);
      } else {
        sessionStorage.removeItem("dj_lastEditAdId");
      }
    }

    // دعم سجل المتصفح (Browser History) للتنقل السلس بأزرار الرجوع والتقدم
    if (pushState && window.history && window.history.pushState) {
      const stateObj = {
        screen: name,
        adId: (name === "details") ? state.currentAdId : null,
        editAdId: (name === "add") ? state.currentEditAdId : null
      };
      const hash = (name === "home") ? "" : "#" + name + (name === "details" && state.currentAdId ? "-" + state.currentAdId : "");
      history.pushState(stateObj, "", window.location.pathname + hash);
    }

    switch (name) {
      case "home": renderAds(); break;
      case "notifications": renderNotifications(); break;
      case "favorites":
        renderAdList("favList", "favEmptyState", ads.filter((a) => state.favorites.has(a.id)));
        break;
      case "mylistings":
        renderAdList("mineList", "mineEmptyState", ads.filter((a) => a.mine));
        break;
      case "admin":
        renderAdminAds();
        break;
      case "settings": updateSettingsPage(); break;
      case "coupons": loadCouponsScreen(); break;
    }

    window.scrollTo({ top: 0, behavior: "auto" });
    closeDrawer();
  }

  // الاستماع لزر الرجوع والتقدم في المتصفح
  window.addEventListener("popstate", (e) => {
    if (e.state && e.state.screen) {
      if (e.state.screen === "details" && e.state.adId) {
        state.currentAdId = e.state.adId;
        renderDetails(e.state.adId);
      }
      goToScreen(e.state.screen, false);
    } else {
      goToScreen("home", false);
    }
  });

  document.addEventListener("click", (e) => {
    const navEl = e.target.closest("[data-nav]");
    if (!navEl) return;

    e.preventDefault();
    const dest = navEl.dataset.nav;

    if (dest === "add") {
      state.currentEditAdId = null;
      const pSec = document.getElementById("paymentSection");
      const addForm = document.getElementById("addForm");
      const imgPrev = document.getElementById("imagePreviewList");
      if (pSec) pSec.style.display = "block";
      if (addForm) addForm.reset();
      if (imgPrev) imgPrev.innerHTML = "";

      const submitBtnSpan = document.querySelector("#submitAdBtn span");
      if (submitBtnSpan) {
        submitBtnSpan.setAttribute("data-i18n", "publishAd");
        submitBtnSpan.textContent = t("publishAd");
      }
    }

    if (navEl.hasAttribute("data-auth-required") && !state.isAuthenticated) {
      state.pendingAction = () => goToScreen(dest);
      openAuth("login");
      return;
    }

    goToScreen(dest);
  });

  function getFilteredAds() {
    const f = state.filters;
    const query = f.query ? f.query.toLowerCase().split(/\s+/).filter(Boolean) : [];

    return ads.slice()
      .filter((ad) => {
        // 1. Basic Filters
        if (f.type !== "all") {
          const adMainType = getMainCategory(ad.type);
          if (adMainType !== f.type) return false;
        }
        if (f.category !== "all" && f.category !== ad.category) return false;
        if (f.governorate !== "all" && ad.governorate !== f.governorate) return false;

        // 2. Smart Search
        if (query.length > 0) {
          const catName = getCategoryName(ad.category, state.lang).toLowerCase();
          const govName = (GOV_MAP[ad.governorate]?.[state.lang] || ad.governorate).toLowerCase();
          const title = ad.title[state.lang].toLowerCase();
          const desc = ad.desc[state.lang].toLowerCase();

          const searchableFields = [title, desc, catName, govName];

          // Every word in the query must be found in at least one field
          return query.every(word => 
            searchableFields.some(field => field.includes(word))
          );
        }
        return true;
      })
      .sort((a, b) => b.createdAt - a.createdAt);
  }

  function adCardHtml(ad) {
    const isFav = state.favorites.has(ad.id);
    const govName = GOV_MAP[ad.governorate] ? GOV_MAP[ad.governorate][state.lang] : ad.governorate;
    const mainCat = getMainCategory(ad.category);
    const catName = getCategoryName(mainCat, state.lang);
    
    let badgeClass = "badge-other";
    if (mainCat === "daily") badgeClass = "badge-daily";
    else if (mainCat === "fulltime") badgeClass = "badge-fulltime";
    else if (mainCat === "ads") badgeClass = "badge-ads";
    else if (mainCat === "services") badgeClass = "badge-services";
    else if (mainCat === "used") badgeClass = "badge-used";
    else if (mainCat === "free") badgeClass = "badge-free";
    else if (mainCat === "real_estate") badgeClass = "badge-realestate";
    else if (mainCat === "cars") badgeClass = "badge-cars";
    else if (mainCat === "rentals" || mainCat === "rental") badgeClass = "badge-rentals";
    
    let priceDisplay = "";
    if (ad.price === 0 || ad.type === "free") {
      priceDisplay = `<span class="ad-price free-price"><small>${t("free")}</small></span>`;
    } else {
      priceDisplay = `<span class="ad-price">${ad.price} <small>${ad.currency || (state.lang === 'ar' ? 'د.أ' : 'JOD')}</small></span>`;
    }
    
    return `
      <article class="ad-card ${ad.mine ? 'mine' : ''}" data-ad-id="${ad.id}">
        <div class="ad-image-wrapper">
          <img src="${ad.image || 'https://placehold.co/400x300/e9ecef/495057?text=Daily+Job'}" alt="Ad Cover" onerror="this.onerror=null; this.src='https://placehold.co/400x300/e9ecef/495057?text=Daily+Job';">
        </div>
        ${ad.mine ? `<span class="ad-mine-tag" style="${ad.status === 'pending' ? 'background:orange;' : (ad.status === 'rejected' ? 'background:red;' : '')}">${ad.status === 'pending' ? (state.lang === 'ar' ? 'قيد المراجعة' : 'Pending') : (ad.status === 'rejected' ? (state.lang === 'ar' ? 'مرفوض' : 'Rejected') : t("myAd"))}</span>` : ''}
        <div class="ad-card-top">
          <span class="ad-badge ${badgeClass}">${catName}</span>
          <h3 class="ad-title">${escapeHtml(ad.title[state.lang])}</h3>
          <button class="ad-fav-btn ${isFav ? 'is-fav' : ''}" data-fav-id="${ad.id}">
            <i class="fa-${isFav ? 'solid' : 'regular'} fa-heart"></i>
          </button>
        </div>
        <div class="ad-meta-row">
          <span><i class="fa-regular fa-clock"></i>${formatRelative(ad.createdAt)}</span>
          <span><i class="fa-solid fa-location-dot"></i>${govName} - ${escapeHtml(ad.area[state.lang])}</span>
          <span><i class="fa-regular fa-eye"></i>${ad.views || 0}</span>
        </div>
        <div class="ad-bottom" style="align-items:flex-start;">
          <button class="ad-contact-btn" data-contact-id="${ad.id}">
            <i class="fa-brands fa-whatsapp"></i> ${t("contact")}
          </button>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px;">
            ${priceDisplay}
          </div>
        </div>
      </article>`;
  }

  function renderAdList(containerId, emptyStateId, arr) {
    const list = document.getElementById(containerId);
    const empty = document.getElementById(emptyStateId);
    if (!list) return;

    if (!arr.length) {
      list.innerHTML = "";
      if (empty) empty.classList.remove("hidden");
    } else {
      if (empty) empty.classList.add("hidden");
      list.innerHTML = arr.map(adCardHtml).join("");
    }

    list.querySelectorAll(".ad-card").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".ad-fav-btn") || e.target.closest(".ad-contact-btn")) return;
        openDetails(card.dataset.adId);
      });
    });

    list.querySelectorAll(".ad-fav-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleFavorite(btn.dataset.favId);
      });
    });

    list.querySelectorAll(".ad-contact-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        handleContact(btn.dataset.contactId);
      });
    });
  }

  async function renderAdminAds() {
    const list = document.getElementById("adminAdsList");
    const empty = document.getElementById("adminEmptyState");
    if (!list) return;
    
    list.innerHTML = '<div style="text-align:center; padding:40px;"><i class="fa-solid fa-spinner fa-spin fa-2x"></i></div>';
    
    try {
       const token = localStorage.getItem("dj_token");
       const res = await fetch(`${BASE_URL}/ads/?status=pending`, { 
         headers: { 'Authorization': 'Token ' + token } 
       });
       const data = await res.json();
       const pendingAds = data.results || data || [];
       
       if (!pendingAds.length) { 
         list.innerHTML = ""; 
         if (empty) empty.classList.remove("hidden"); 
       } else { 
         if (empty) empty.classList.add("hidden"); 
         list.innerHTML = pendingAds.map(ad => {
           const adTitle = typeof ad.title === 'object' ? (ad.title.ar || ad.title.en) : ad.title;
           const adDesc = typeof ad.description === 'object' ? (ad.description.ar || ad.description.en) : ad.description;
           
           // Build images for admin panel
           const allImages = [];
           if (ad.image) allImages.push(ad.image);
           if (ad.extra_images && ad.extra_images.length > 0) {
             ad.extra_images.forEach(img => {
               if (img.image && !allImages.includes(img.image)) allImages.push(img.image);
             });
           }
           let imagesHtml = '';
           if (allImages.length > 1) {
             imagesHtml = `
               <div style="display:flex; overflow-x:auto; gap:8px; padding:10px 15px; background:#f8f9fa;">
                 ${allImages.map(src => `<a href="${src}" target="_blank"><img src="${src}" onerror="this.onerror=null; this.src='https://placehold.co/100x100/e9ecef/495057?text=Daily+Job';" style="height:100px; min-width:100px; object-fit:cover; border-radius:8px; border:1px solid #dee2e6;"></a>`).join('')}
               </div>
             `;
           } else if (allImages.length === 1) {
             imagesHtml = `<a href="${allImages[0]}" target="_blank"><img src="${allImages[0]}" onerror="this.onerror=null; this.src='https://placehold.co/400x180/e9ecef/495057?text=Daily+Job';" style="width:100%; height:180px; object-fit:cover;"></a>`;
           }

          return `
            <div class="ad-card" data-ad-id="${ad.id}">
              ${imagesHtml}
              <div class="ad-card-top" style="padding:15px; display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="flex:1; min-width:0;">
                  <h3 class="ad-title" style="margin-bottom:5px;">${escapeHtml(adTitle)}</h3>
                  <p class="ad-desc" style="margin-bottom:8px;">${escapeHtml(adDesc).substring(0,80)}...</p>
                  
                  <div class="tag-row" style="margin-bottom: 8px;">
                    <span class="badge badge-other">${escapeHtml(ad.category || '')}</span>
                    <span class="badge badge-other"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(ad.governorate || '')}</span>
                    <span class="badge badge-other"><i class="fa-solid fa-money-bill"></i> ${ad.price} JOD</span>
                  </div>
                </div>
                
                ${ad.receipt_image ? `
                  <div style="margin-right: 10px; flex-shrink:0; text-align:center;">
                    <p style="margin:0 0 4px 0; font-size:11px; color:var(--ink-500);">وصل الدفع</p>
                    <a href="${ad.receipt_image}" target="_blank">
                      <img src="${ad.receipt_image}" onerror="this.onerror=null; this.src='https://placehold.co/70x70/e9ecef/495057?text=Receipt';" style="width:70px;height:70px;object-fit:cover;border-radius:8px; border:2px solid var(--line);">
                    </a>
                  </div>` : '<p style="color:var(--orange-500); font-size:12px; margin:0;"><i class="fa-solid fa-triangle-exclamation"></i> لا يوجد وصل</p>'}
              </div>
              <div class="ad-bottom" style="display:flex; gap:10px; padding:12px 15px; border-top:1px solid var(--line);">
                <button class="btn-primary admin-approve-btn" data-id="${ad.id}" style="background:var(--green-500);border:none;flex:1;"><i class="fa-solid fa-check"></i> قبول</button>
                <button class="btn-outline admin-reject-btn" data-id="${ad.id}" style="color:var(--red-500);border-color:var(--red-500);flex:1;"><i class="fa-solid fa-xmark"></i> رفض</button>
              </div>
            </div>`;
         }).join(""); 
         
          // Attach events
          list.querySelectorAll(".admin-approve-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
              const card = btn.closest(".ad-card");
              const siblingBtn = card ? card.querySelector(".admin-reject-btn") : null;
              btn.disabled = true;
              if (siblingBtn) siblingBtn.disabled = true;
              btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> جاري القبول...';
              try {
                const r = await fetch(`${BASE_URL}/ads/${btn.dataset.id}/action/`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', 'Authorization': 'Token ' + token },
                  body: JSON.stringify({ action: 'approve' })
                });
                if (r.ok) {
                  showToast("تم قبول الإعلان ونشره بنجاح", "success");
                  if (card) {
                    card.style.transition = "opacity 0.25s ease, transform 0.25s ease";
                    card.style.opacity = "0";
                    card.style.transform = "scale(0.95)";
                    setTimeout(() => {
                      card.remove();
                      if (!list.querySelectorAll(".ad-card").length && empty) {
                        empty.classList.remove("hidden");
                      }
                    }, 250);
                  }
                } else {
                  const errData = await r.json().catch(() => ({}));
                  throw new Error(errData.error || "فشل قبول الإعلان");
                }
              } catch(e) {
                showToast(e.message || "حدث خطأ أثناء قبول الإعلان", "error");
                btn.disabled = false;
                if (siblingBtn) siblingBtn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> قبول';
              }
            });
          });
          
          list.querySelectorAll(".admin-reject-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
              if (!confirm("هل أنت متأكد من رفض هذا الإعلان؟")) return;
              const card = btn.closest(".ad-card");
              const siblingBtn = card ? card.querySelector(".admin-approve-btn") : null;
              btn.disabled = true;
              if (siblingBtn) siblingBtn.disabled = true;
              btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> جاري الرفض...';
              try {
                const r = await fetch(`${BASE_URL}/ads/${btn.dataset.id}/action/`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', 'Authorization': 'Token ' + token },
                  body: JSON.stringify({ action: 'reject' })
                });
                if (r.ok) {
                  showToast("تم رفض الإعلان", "success");
                  if (card) {
                    card.style.transition = "opacity 0.25s ease, transform 0.25s ease";
                    card.style.opacity = "0";
                    card.style.transform = "scale(0.95)";
                    setTimeout(() => {
                      card.remove();
                      if (!list.querySelectorAll(".ad-card").length && empty) {
                        empty.classList.remove("hidden");
                      }
                    }, 250);
                  }
                } else {
                  const errData = await r.json().catch(() => ({}));
                  throw new Error(errData.error || "فشل رفض الإعلان");
                }
              } catch(e) {
                showToast(e.message || "حدث خطأ أثناء رفض الإعلان", "error");
                btn.disabled = false;
                if (siblingBtn) siblingBtn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-xmark"></i> رفض';
              }
            });
          });
       }
    } catch(err) {
       list.innerHTML = `<div style="text-align:center; color:red; padding:20px;">${err.message}</div>`;
    }
  }

  function renderAds() {
    const filtered = getFilteredAds();
    renderAdList("adsList", "homeEmptyState", filtered);

    const countEl = document.getElementById("resultsCount");
    if (countEl) countEl.textContent = `(${filtered.length})`;

    updateActiveFiltersDisplay();
  }

  // ===== تعديل 5: Lightbox =====
  let _lightboxImages = [];
  let _lightboxIdx = 0;
  let _lightboxZoom = 1;

  function openLightbox(images, startIdx = 0) {
    _lightboxImages = images;
    _lightboxIdx = startIdx;
    _lightboxZoom = 1;

    // إنشاء الـ Lightbox إذا لم يكن موجوداً
    let lb = document.getElementById("lbOverlay");
    if (!lb) {
      lb = document.createElement("div");
      lb.id = "lbOverlay";
      lb.style.cssText = `
        position:fixed; inset:0; z-index:9999; background:rgba(0,0,0,0.92);
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        touch-action:pinch-zoom;
      `;
      lb.innerHTML = `
        <button id="lbClose" style="position:absolute;top:16px;right:16px;background:rgba(255,255,255,0.15);border:none;
          color:#fff;font-size:24px;width:44px;height:44px;border-radius:50%;cursor:pointer;z-index:1;
          display:flex;align-items:center;justify-content:center;">✕</button>
        <button id="lbPrev" style="position:absolute;left:12px;top:50%;transform:translateY(-50%);background:rgba(255,255,255,0.15);
          border:none;color:#fff;font-size:26px;width:44px;height:44px;border-radius:50%;cursor:pointer;z-index:1;
          display:flex;align-items:center;justify-content:center;">‹</button>
        <div id="lbImgWrap" style="max-width:95vw;max-height:85vh;overflow:hidden;display:flex;align-items:center;justify-content:center;">
          <img id="lbImg" style="max-width:95vw;max-height:85vh;object-fit:contain;transition:transform 0.2s;transform-origin:center;cursor:zoom-in;border-radius:6px;">
        </div>
        <button id="lbNext" style="position:absolute;right:12px;top:50%;transform:translateY(-50%);background:rgba(255,255,255,0.15);
          border:none;color:#fff;font-size:26px;width:44px;height:44px;border-radius:50%;cursor:pointer;z-index:1;
          display:flex;align-items:center;justify-content:center;">›</button>
        <div id="lbCounter" style="position:absolute;bottom:20px;color:#fff;font-size:13px;opacity:0.7;"></div>
      `;
      document.body.appendChild(lb);

      document.getElementById("lbClose").addEventListener("click", closeLightbox);
      lb.addEventListener("click", e => { if (e.target === lb) closeLightbox(); });
      document.getElementById("lbPrev").addEventListener("click", e => { e.stopPropagation(); lbNav(-1); });
      document.getElementById("lbNext").addEventListener("click", e => { e.stopPropagation(); lbNav(1); });

      // Zoom بالضغط على الصورة
      document.getElementById("lbImg").addEventListener("click", e => {
        e.stopPropagation();
        _lightboxZoom = _lightboxZoom > 1 ? 1 : 2.5;
        const img = document.getElementById("lbImg");
        img.style.transform = `scale(${_lightboxZoom})`;
        img.style.cursor = _lightboxZoom > 1 ? "zoom-out" : "zoom-in";
      });

      // Keyboard navigation
      document.addEventListener("keydown", lbKeyHandler);

      // Touch swipe
      let touchStartX = 0;
      lb.addEventListener("touchstart", e => { touchStartX = e.touches[0].clientX; }, { passive: true });
      lb.addEventListener("touchend", e => {
        const dx = e.changedTouches[0].clientX - touchStartX;
        if (Math.abs(dx) > 50) lbNav(dx < 0 ? 1 : -1);
      });
    }

    lb.style.display = "flex";
    lbRender();
  }

  function lbRender() {
    const img = document.getElementById("lbImg");
    const counter = document.getElementById("lbCounter");
    const prev = document.getElementById("lbPrev");
    const next = document.getElementById("lbNext");
    if (!img) return;

    _lightboxZoom = 1;
    img.style.transform = "scale(1)";
    img.style.cursor = "zoom-in";
    img.src = _lightboxImages[_lightboxIdx];
    if (counter) counter.textContent = `${_lightboxIdx + 1} / ${_lightboxImages.length}`;
    if (prev) prev.style.display = _lightboxImages.length > 1 ? "flex" : "none";
    if (next) next.style.display = _lightboxImages.length > 1 ? "flex" : "none";
  }

  function lbNav(dir) {
    _lightboxIdx = (_lightboxIdx + dir + _lightboxImages.length) % _lightboxImages.length;
    lbRender();
  }

  function lbKeyHandler(e) {
    const lb = document.getElementById("lbOverlay");
    if (!lb || lb.style.display === "none") return;
    if (e.key === "Escape") closeLightbox();
    else if (e.key === "ArrowLeft") lbNav(-1);
    else if (e.key === "ArrowRight") lbNav(1);
  }

  function closeLightbox() {
    const lb = document.getElementById("lbOverlay");
    if (lb) lb.style.display = "none";
    _lightboxZoom = 1;
  }
  // ===== نهاية Lightbox =====

  function showDetailsLoading() {
    const titleEl = document.getElementById("detailsTitle");
    if (titleEl) titleEl.textContent = state.lang === 'ar' ? "جاري تحميل تفاصيل الإعلان..." : "Loading ad details...";
    const descEl = document.getElementById("descText");
    if (descEl) descEl.textContent = "";
    const tagsContainer = document.getElementById("detailsTags");
    if (tagsContainer) tagsContainer.innerHTML = "";
    const priceBig = document.getElementById("priceBig");
    if (priceBig) priceBig.textContent = "—";
    const phoneVal = document.getElementById("phoneValue");
    if (phoneVal) phoneVal.textContent = "—";
    const detailsCard = document.querySelector(".details-card");
    if (detailsCard) {
      const oldImg = detailsCard.querySelector(".ad-details-image-wrapper");
      if (oldImg) oldImg.remove();
    }
  }

  async function openDetails(adId) {
    if (!state.isAuthenticated) {
      state.pendingAction = () => {
        state.currentAdId = adId;
        openDetails(adId);
      };
      openAuth("login");
      return;
    }

    state.currentAdId = adId;
    let existingAd = ads.find(a => String(a.id) === String(adId));
    if (existingAd) {
      renderDetails(adId);
      goToScreen("details");
    } else {
      showDetailsLoading();
      goToScreen("details");
    }

    // جلب الإعلان من السيرفر لتسجيل المشاهدة وتحديث العداد في الوقت الفعلي
    try {
      const dbAd = await Api.getAd(adId);
      if (dbAd) {
        const mapped = mapDbAd(dbAd);
        const idx = ads.findIndex(a => String(a.id) === String(adId));
        if (idx >= 0) {
          ads[idx] = mapped;
        } else {
          ads.push(mapped);
        }
        renderDetails(adId);
      }
    } catch (err) {
      console.warn("Could not refresh ad details", err);
      if (!existingAd) {
        showToast(state.lang === 'ar' ? "الإعلان غير متوفر أو تم حذفه" : "Ad is no longer available or deleted", "error");
        const lastScreen = sessionStorage.getItem("dj_lastScreen") || "home";
        goToScreen(lastScreen !== "details" ? lastScreen : "home");
      }
    }
  }

  function renderDetails(adId) {
    const ad = ads.find((a) => String(a.id) === String(adId));
    if (!ad) return;

    const isFav = state.favorites.has(ad.id);
    const govName = GOV_MAP[ad.governorate] ? GOV_MAP[ad.governorate][state.lang] : ad.governorate;
    const mainCat = getMainCategory(ad.category);
    const catName = getCategoryName(mainCat, state.lang);

    const detailsCard = document.querySelector(".details-card");
    if (detailsCard) {
      const oldImg = detailsCard.querySelector(".ad-details-image-wrapper");
      if (oldImg) oldImg.remove();

      // Build images list: main + extra
      const allImages = [];
      if (ad.image) allImages.push(ad.image);
      if (ad.extra_images && ad.extra_images.length > 0) {
        ad.extra_images.forEach(img => {
          if (img.image && !allImages.includes(img.image)) allImages.push(img.image);
        });
      }

      // تعديل 5: Lightbox — معرض صور مع تكبير عند الضغط
      // === تصميم: صورة رئيسية + مصغرات مربعة ===
      const mainSrc = allImages[0] || 'https://placehold.co/800x400/e9ecef/495057?text=Daily+Job';

      let imgHtml = `
        <div class="ad-details-image-wrapper" id="adGalleryWrapper">
          <!-- الصورة الرئيسية -->
          <img id="adMainImage"
            src="${mainSrc}"
            alt="الصورة الرئيسية"
            onerror="this.onerror=null; this.src='https://placehold.co/800x400/e9ecef/495057?text=Daily+Job';"
            data-lightbox-src="${mainSrc}"
            data-lightbox-idx="0"
            style="width:100%; height:280px; object-fit:cover; cursor:zoom-in; display:block; border-radius:12px 12px 0 0;">

          ${allImages.length > 1 ? `
          <!-- المصغرات -->
          <div id="adThumbnails" style="
            display:flex; gap:6px; padding:8px 10px;
            background:#f8f9fa; border-radius:0 0 12px 12px;
            overflow-x:auto; -webkit-overflow-scrolling:touch;
          ">
            ${allImages.map((src, i) => `
              <img
                src="${src}"
                alt="صورة ${i+1}"
                onerror="this.onerror=null; this.src='https://placehold.co/100x100/e9ecef/495057?text=Daily+Job';"
                class="ad-thumb ${i === 0 ? 'thumb-active' : ''}"
                data-idx="${i}"
                style="
                  width:64px; height:64px; object-fit:cover;
                  border-radius:8px; flex-shrink:0; cursor:pointer;
                  border: 2px solid ${i === 0 ? 'var(--orange)' : '#dee2e6'};
                  transition: border-color 0.2s, transform 0.15s;
                "
              >
            `).join('')}
          </div>` : ''}
        </div>`;

      detailsCard.insertAdjacentHTML("afterbegin", imgHtml);

      // === ربط أحداث المعرض ===
      const mainImg = detailsCard.querySelector("#adMainImage");
      const thumbs  = detailsCard.querySelectorAll(".ad-thumb");

      // Lightbox عند الضغط على الصورة الرئيسية
      if (mainImg) {
        mainImg.addEventListener("click", () => {
          const idx = parseInt(mainImg.getAttribute("data-lightbox-idx") || "0");
          openLightbox(allImages, idx);
        });
      }

      // تبديل الصورة الرئيسية عند الضغط على مصغرة
      thumbs.forEach(thumb => {
        thumb.addEventListener("click", () => {
          const idx = parseInt(thumb.dataset.idx);
          if (mainImg) {
            mainImg.src = allImages[idx];
            mainImg.setAttribute("data-lightbox-idx", idx);
          }
          thumbs.forEach(t => {
            t.style.border = "2px solid #dee2e6";
            t.classList.remove("thumb-active");
          });
          thumb.style.border = "2px solid var(--orange)";
          thumb.classList.add("thumb-active");
        });
      });
    }

    const deleteAdBtn = document.getElementById("deleteAdBtn");
    const editAdBtn = document.getElementById("editAdBtn");
    if (state.user && state.user.email && ad.user_email && state.user.email.toLowerCase() === ad.user_email.toLowerCase()) {
      if (deleteAdBtn) deleteAdBtn.classList.remove("hidden");
      if (editAdBtn) editAdBtn.classList.remove("hidden");
    } else {
      if (deleteAdBtn) deleteAdBtn.classList.add("hidden");
      if (editAdBtn) editAdBtn.classList.add("hidden");
    }

    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setTxt("detailsTitle", ad.title[state.lang]);
    setTxt("metaTime", formatRelative(ad.createdAt));
    setTxt("metaLoc", `${govName} - ${ad.area[state.lang]}`);
    setTxt("metaViews", `${ad.views || 0} ${state.lang === 'ar' ? 'مشاهدة' : 'views'}`);
    setTxt("metaCat", catName);
    setTxt("descText", ad.desc[state.lang]);
    setTxt("priceCurrency", ad.currency);

    const priceBig = document.getElementById("priceBig");
    const priceUnit = document.getElementById("priceUnit");
    if (priceBig) {
      if (ad.price === 0 || ad.type === "free") {
        priceBig.textContent = t("free");
        priceBig.classList.add("is-free");
        if (priceUnit) priceUnit.textContent = "";
      } else {
        priceBig.textContent = ad.price;
        priceBig.classList.remove("is-free");
        if (priceUnit) {
          priceUnit.textContent = "";
          priceUnit.innerHTML = "";
        }
      }
    }

    const tagsContainer = document.getElementById("detailsTags");
    if (tagsContainer) {
      let statusPill = "";
      if (ad.status === 'pending') {
        statusPill = `<span class="pill" style="background:#f59e0b; color:#fff;">${state.lang === 'ar' ? '⏳ قيد المراجعة' : '⏳ Pending Review'}</span>`;
      } else if (ad.status === 'rejected') {
        statusPill = `<span class="pill" style="background:#ef4444; color:#fff;">${state.lang === 'ar' ? '❌ مرفوض' : '❌ Rejected'}</span>`;
      }
      tagsContainer.innerHTML = `
        <span class="pill pill-orange">${catName}</span>
        <span class="pill pill-outline">${govName}</span>
        ${statusPill}
      `;
    }

    const favBtn = document.getElementById("favBtn");
    if (favBtn) {
      favBtn.className = `icon-round ${isFav ? 'is-fav' : ''}`;
      favBtn.innerHTML = `<i class="fa-${isFav ? 'solid' : 'regular'} fa-heart"></i>`;
    }

    const phoneVal = document.getElementById("phoneValue");
    if (phoneVal) phoneVal.textContent = ad.phone;

    const callBtn = document.getElementById("callBtn");
    if (callBtn) callBtn.href = `tel:${ad.phone}`;
  }

  const contactBtnEl = document.getElementById("contactBtn");
  if (contactBtnEl) {
    contactBtnEl.addEventListener("click", () => {
      handleContact(state.currentAdId);
    });
  }

  const detailsBackBtn = document.getElementById("detailsBackBtn");
  if (detailsBackBtn) {
    detailsBackBtn.addEventListener("click", () => {
      const lastScreen = sessionStorage.getItem("dj_lastScreen");
      if (lastScreen && lastScreen !== "details") {
        goToScreen(lastScreen);
      } else if (window.history.length > 1) {
        window.history.back();
      } else {
        goToScreen("home");
      }
    });
  }

  function handleContact(adId) {
    const ad = ads.find((a) => String(a.id) === String(adId));
    if (!ad || !ad.phone) return;
    const cleanPhone = String(ad.phone).replace(/\D/g, '').replace(/^0/, '');
    const phoneNumber = `962${cleanPhone}`;
    if (ad.contactMethod === "whatsapp" || ad.contactMethod === "both") {
      const title = (ad.title && typeof ad.title === 'object') ? (ad.title[state.lang] || ad.title.ar || '') : (ad.title || '');
      const greeting = state.lang === 'ar'
        ? `مرحباً، أتواصل معك بخصوص إعلانك "${title}" على منصة Daily Job.`
        : `Hello, I'm contacting you regarding your ad "${title}" on Daily Job.`;
      const encodedMsg = encodeURIComponent(greeting);
      window.open(`https://wa.me/${phoneNumber}?text=${encodedMsg}`, "_blank");
    } else if (ad.contactMethod === "call") {
      window.open(`tel:+${phoneNumber}`, "_blank");
    }
  }

  const shareBtn = document.getElementById("shareBtn");
  if (shareBtn) {
    shareBtn.addEventListener("click", () => {
      const ad = ads.find((a) => a.id === state.currentAdId);
      if (ad && navigator.share) {
        navigator.share({
          title: ad.title[state.lang],
          text: ad.desc[state.lang],
          url: window.location.href
        }).catch(() => {});
      } else {
        showToast(t("sharingNotSupported"), "info");
      }
    });
  }

  const favBtnDet = document.getElementById("favBtn");
  if (favBtnDet) {
    favBtnDet.addEventListener("click", () => {
      toggleFavorite(state.currentAdId);
      renderDetails(state.currentAdId);
    });
  }

  function toggleFavorite(adId) {
    if (state.favorites.has(adId)) {
      state.favorites.delete(adId);
      showToast(t("removedFromFav"), "info");
    } else {
      state.favorites.add(adId);
      showToast(t("addedToFav"), "success");
    }
    localStorage.setItem("dj_favorites", JSON.stringify([...state.favorites]));
    
    const activeScreen = document.querySelector(".screen.active");
    if (activeScreen && activeScreen.id === "screen-favorites") {
      renderAdList("favList", "favEmptyState", ads.filter((a) => state.favorites.has(a.id)));
    } else if (activeScreen && activeScreen.id === "screen-home") {
      renderAds();
    }
  }

  function openDrawer() {
    updateDrawerUser();
    if (elements.drawerOverlay) elements.drawerOverlay.classList.add("open");
  }

  function closeDrawer() {
    if (elements.drawerOverlay) elements.drawerOverlay.classList.remove("open");
  }

  function updateDrawerUser() {
    const nameEl = document.getElementById("drawerUserName");
    const subEl = document.getElementById("drawerUserSub");
    const authBtnLabel = document.getElementById("drawerAuthLabel");
    const avatarEl = document.getElementById("drawerAvatar");

    if (!nameEl) return;

    const adminDrawerItem = document.getElementById("adminDrawerItem");

    if (state.isAuthenticated && state.user) {
      nameEl.textContent = state.user.username;
      if (subEl) subEl.textContent = state.user.email;
      if (authBtnLabel) authBtnLabel.textContent = t("logout");
      if (avatarEl) {
        avatarEl.innerHTML = `<i class="fa-solid fa-user-check"></i>`;
        avatarEl.style.background = "var(--orange-tint)";
      }
      if (adminDrawerItem) {
        if (state.user.role === 'admin') adminDrawerItem.classList.remove("hidden");
        else adminDrawerItem.classList.add("hidden");
      }
    } else {
      nameEl.textContent = t("guest");
      if (subEl) subEl.textContent = t("signInToSeeMore");
      if (authBtnLabel) authBtnLabel.textContent = t("login");
      if (avatarEl) {
        avatarEl.innerHTML = `<i class="fa-regular fa-user"></i>`;
        avatarEl.style.background = "var(--orange-tint)";
      }
      if (adminDrawerItem) adminDrawerItem.classList.add("hidden");
    }
  }

  const menuBtn = document.getElementById("menuBtn");
  const drawerClose = document.getElementById("drawerClose");
  const drawerAuthBtn = document.getElementById("drawerAuthBtn");

  if (menuBtn) menuBtn.addEventListener("click", openDrawer);
  if (drawerClose) drawerClose.addEventListener("click", closeDrawer);
  if (elements.drawerOverlay) {
    elements.drawerOverlay.addEventListener("click", (e) => {
      if (e.target === elements.drawerOverlay) closeDrawer();
    });
  }
  if (drawerAuthBtn) {
    drawerAuthBtn.addEventListener("click", () => {
      closeDrawer();
      if (state.isAuthenticated) logout();
      else openAuth("login");
    });
  }

  function renderNotifications() {
    const list = document.getElementById("notifList");
    const emptyState = document.getElementById("notifEmptyState");
    const deleteAllBtn = document.getElementById("deleteAllNotifsBtn");
    if (!list) return;

    // استخدام is_read من السيرفر
    const unreadCount = state.notifications.filter(n => !n.is_read).length;
    const notifDot = document.getElementById("headerNotifDot");
    if (notifDot) {
      if (unreadCount > 0) notifDot.classList.remove("hidden");
      else notifDot.classList.add("hidden");
    }

    if (state.notifications.length === 0) {
      list.innerHTML = "";
      if (emptyState) emptyState.classList.remove("hidden");
      if (deleteAllBtn) deleteAllBtn.style.display = "none";
      return;
    }

    if (deleteAllBtn) deleteAllBtn.style.display = "flex";
    if (emptyState) emptyState.classList.add("hidden");
    list.innerHTML = state.notifications.map((n) => `
      <div class="notif-item ${n.is_read ? "" : "unread"}" data-notif-id="${n.id}" data-ad-id="${n.ad_id || ''}" style="cursor:pointer;">
        <div class="notif-icon"><i class="fa-solid fa-bell"></i></div>
        <div class="notif-body">
          <div class="notif-title">${escapeHtml(n.title)}</div>
          <div class="notif-text">${escapeHtml(n.message)}</div>
          <div class="notif-time">${formatRelative(new Date(n.created_at))}</div>
        </div>
        <button class="notif-delete-btn" data-delete-id="${n.id}" title="${state.lang === 'ar' ? 'حذف الإشعار' : 'Delete notification'}">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>`).join("");

    list.querySelectorAll(".notif-item").forEach(item => {
      item.addEventListener("click", (e) => {
        if (e.target.closest(".notif-delete-btn")) return;

        // وضع علامة مقروء فوراً
        const notifId = item.dataset.notifId;
        const notif = state.notifications.find(n => String(n.id) === String(notifId));
        if (notif && !notif.is_read) {
          notif.is_read = true;
          item.classList.remove("unread");
          updateNotificationDot();
          const token = localStorage.getItem("dj_token");
          if (token) Api.markNotificationRead(notifId, token);
        }

        const adId = (item.getAttribute("data-ad-id") || '').trim();
        const fullText = (item.textContent || '').toLowerCase();

        if (adId && adId !== '' && adId !== 'null' && adId !== 'undefined') {
          openDetails(adId);
        } else if (state.user && state.user.role === 'admin' && (fullText.includes('إيصال') || fullText.includes('دفع') || fullText.includes('مراجعة') || fullText.includes('receipt'))) {
          goToScreen('admin');
        } else if (fullText.includes('قسيمة') || fullText.includes('كوبون') || fullText.includes('هدية') || fullText.includes('كود') || fullText.includes('coupon')) {
          goToScreen('coupons');
        } else if (fullText.includes('إعلان') || fullText.includes('ad')) {
          if (state.user && state.user.role === 'admin') {
            goToScreen('admin');
          } else {
            goToScreen('mylistings');
          }
        }
      });
    });

    // حذف إشعار فردي
    list.querySelectorAll(".notif-delete-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const notifId = btn.dataset.deleteId;
        if (!notifId) return;

        state.notifications = state.notifications.filter(n => String(n.id) !== String(notifId));
        renderNotifications();
        updateNotificationDot();
        showToast(state.lang === 'ar' ? "تم حذف الإشعار" : "Notification deleted", "info");

        const token = localStorage.getItem("dj_token");
        if (token) {
          Api.deleteNotifications([notifId], token);
        }
      });
    });
  }

  const markAllReadBtn = document.getElementById("markAllReadBtn");
  if (markAllReadBtn) {
    markAllReadBtn.addEventListener("click", () => {
      state.notifications.forEach((n) => (n.is_read = true));
      renderNotifications();
      updateNotificationDot();
      showToast(t("allMarkedRead"), "success");
      const token = localStorage.getItem("dj_token");
      if (token) Api.markAllNotificationsRead(token);
    });
  }

  const deleteAllNotifsBtn = document.getElementById("deleteAllNotifsBtn");
  if (deleteAllNotifsBtn) {
    deleteAllNotifsBtn.addEventListener("click", async () => {
      if (!state.notifications || state.notifications.length === 0) return;

      const confirmed = window.confirm(
        state.lang === 'ar'
          ? "هل أنت متأكد من حذف جميع الإشعارات؟"
          : "Are you sure you want to delete all notifications?"
      );
      if (!confirmed) return;

      state.notifications = [];
      renderNotifications();
      updateNotificationDot();
      showToast(state.lang === 'ar' ? "تم حذف جميع الإشعارات بنجاح" : "All notifications deleted", "info");

      const token = localStorage.getItem("dj_token");
      if (token) {
        Api.deleteNotifications('all', token);
      }
    });
  }

  function updateNotificationDot() {
    const unreadCount = state.notifications.filter(n => !n.is_read).length;
    const notifDot = document.getElementById("headerNotifDot");
    if (notifDot) {
      if (unreadCount > 0) notifDot.classList.remove("hidden");
      else notifDot.classList.add("hidden");
    }
  }

  function populateFormSelects() {
    const govSelect = document.getElementById("fGovernorate");
    if (govSelect) {
      govSelect.innerHTML = GOVERNORATES.map((g) => `<option value="${g.key}">${g.en}</option>`).join("");
    }

    const settingsGovSelect = document.getElementById("settingsGov");
    if (settingsGovSelect) {
      settingsGovSelect.innerHTML = `
        <option value="all">— ${t("all")} —</option>
        ${GOVERNORATES.map((g) => `<option value="${g.key}">${g.en}</option>`).join("")}
      `;
    }

    const filterGovSelect = document.getElementById("filterGovSelect");
    if (filterGovSelect) {
      filterGovSelect.innerHTML = `
        <option value="all">— ${t("all")} —</option>
        ${GOVERNORATES.map((g) => `<option value="${g.key}">${g.en}</option>`).join("")}
      `;
    }

    const filterCategoryChips = document.getElementById("filterCategoryChips");
    if (filterCategoryChips) {
      const mainCategories = CATEGORIES.filter(c => !c.parent);
      filterCategoryChips.innerHTML = mainCategories.map((c) => 
        `<button type="button" data-cat="${c.key}" class="${state.filters.category === c.key ? 'active' : ''}">${c[state.lang]}</button>`
      ).join("");

      filterCategoryChips.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("click", () => {
          filterCategoryChips.querySelectorAll("button").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
        });
      });
    }
  }

  function openEdit(adId) {
    const ad = ads.find(a => a.id === adId);
    if (!ad) return;

    state.currentEditAdId = ad.id;
    sessionStorage.setItem("dj_lastEditAdId", ad.id);

    const pSec = document.getElementById("paymentSection");
    if (pSec) pSec.style.display = "none";

    const submitBtnSpan = document.querySelector("#submitAdBtn span");
    if (submitBtnSpan) {
      submitBtnSpan.setAttribute("data-i18n", "saveChanges");
      submitBtnSpan.textContent = t("saveChanges");
    }

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val;
    };

    setVal("fTitle", ad.title.en);
    setVal("fGovernorate", ad.governorate);
    setVal("fCategory", ad.category);
    setVal("fWage", ad.price);
    setVal("fDetails", ad.desc.en);
    setVal("fContactMethod", ad.contactMethod);
    setVal("fPhone", ad.phone);

    goToScreen("add");
  }

  const editAdBtn = document.getElementById("editAdBtn");
  if (editAdBtn) {
    editAdBtn.addEventListener("click", () => {
      openEdit(state.currentAdId);
    });
  }

  async function performSave() {
    let btn = document.getElementById("submitAdBtn");
    if (!state.currentEditAdId) {
      btn = document.getElementById("confirmCliqBtn") || btn;
    }
    const originalText = btn ? btn.innerHTML : '';
    try {
      if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        btn.disabled = true;
      }

      const token = localStorage.getItem("dj_token");
      if (!token) {
        showToast("يرجى تسجيل الدخول أولاً", "error");
        openAuth("login");
        throw new Error("User not authenticated");
      }

      const formData = new FormData();
      formData.append("title", document.getElementById("fTitle").value.trim());
      formData.append("description", document.getElementById("fDetails").value.trim());
      formData.append("category", document.getElementById("fCategory").value.trim());
      formData.append("governorate", document.getElementById("fGovernorate").value.trim());
      formData.append("price", parseFloat(document.getElementById("fWage").value.trim()) || 0);
      formData.append("contact_phone", document.getElementById("fPhone").value.trim());
      formData.append("contact_method", document.getElementById("fContactMethod").value);
      const fAdDuration = document.getElementById("fAdDuration");
      if (fAdDuration) {
        formData.append("ad_duration", fAdDuration.value);
      }
      
      const imagesInput = document.getElementById("fImages");
      if (imagesInput && imagesInput.files && imagesInput.files.length > 0) {
        // First image as the main image field
        formData.append("image", imagesInput.files[0]);
        // All images as extra images
        Array.from(imagesInput.files).forEach(file => {
          formData.append("images", file);
        });
      }
      
      const receiptInput = document.getElementById("fReceipt");
      if (receiptInput && receiptInput.files && receiptInput.files[0]) {
        formData.append("receipt_image", receiptInput.files[0]);
      }

      const headers = { 
        'Authorization': 'Token ' + token 
      };

      const parseError = async (res, defaultMsg) => {
        if (res.status === 401) {
          localStorage.removeItem("dj_token");
          localStorage.removeItem("dj_user");
          showToast("انتهت الجلسة، يرجى تسجيل الدخول مجدداً", "error");
          openAuth("login");
          return "انتهت الجلسة، يرجى تسجيل الدخول مجدداً";
        }
        try {
          const errData = await res.json();
          if (errData && typeof errData === "object") {
            const msgs = [];
            for (const [k, v] of Object.entries(errData)) {
              const valStr = Array.isArray(v) ? v.join(", ") : String(v);
              msgs.push(valStr);
            }
            if (msgs.length > 0) return msgs.join(" | ");
          } else if (typeof errData === "string") {
            return errData;
          }
        } catch (_) {
          try {
            const text = await res.text();
            if (text && text.length < 150) return text;
          } catch (_) {}
        }
        return defaultMsg;
      };

      if (state.currentEditAdId) {
        const res = await fetch(`${BASE_URL}/ads/${state.currentEditAdId}/`, {
          method: 'PATCH',
          headers: headers,
          body: formData
        });
        if (!res.ok) {
          const msg = await parseError(res, "حدث خطأ أثناء تعديل الإعلان.");
          throw new Error(msg);
        }
        showToast("تم تعديل الإعلان بنجاح", "success");
        state.currentEditAdId = null;
      } else {
        const res = await fetch(`${BASE_URL}/ads/`, {
          method: 'POST',
          headers: headers,
          body: formData
        });
        if (!res.ok) {
          const msg = await parseError(res, "حدث خطأ أثناء النشر.");
          throw new Error(msg);
        }
        showToast(t("adPublished"), "success");
      }

      await loadAdsFromAPI();
      
      if (elements.cliqModalOverlay) {
        elements.cliqModalOverlay.classList.remove("open");
      }
      
      const addForm = document.getElementById("addForm");
      if (addForm) addForm.reset();
      
      const imgPreview = document.getElementById("imagePreviewList");
      if (imgPreview) imgPreview.innerHTML = "";
      const receiptPreview = document.getElementById("receiptPreviewList");
      if (receiptPreview) receiptPreview.innerHTML = "";
      
      goToScreen("home");

    } catch (error) {
      if (error.message !== "User not authenticated") {
        let errEl = document.getElementById("addFormError");
        if (!state.currentEditAdId) {
           errEl = document.getElementById("cliqModalError") || errEl;
        }
        if (errEl) showFormError(errEl, error.message || "حدث خطأ.");
        else showToast(error.message, "error");
      }
      throw error;
    } finally {
      if (btn) {
        btn.innerHTML = originalText;
        btn.disabled = false;
      }
    }
  }

  const addFormEl = document.getElementById("addForm");
  if (addFormEl) {
    // ── تحديث بطاقة سياسة الأجر عند تغيير التصنيف ──────────────────────
    function updateWagePolicyBox() {
      const fCategory = document.getElementById("fCategory");
      const durationContainer = document.getElementById("adDurationContainer");
      const durationEl = document.getElementById("fAdDuration");
      const btnSpan = document.querySelector("#submitAdBtn span");
      
      if (!fCategory) return;
      
      const category = fCategory.value;
      const isAr = state.lang === "ar";

      if (category === "daily" || category === "free" || category === "ads") {
        if (durationContainer) durationContainer.style.display = "none";
        if (durationEl) durationEl.value = "1_day";
      } else {
        if (durationContainer) durationContainer.style.display = "block";
      }
      
      // Update fee text
      const fee = (durationEl && durationEl.value === '1_week') ? 2 : 1;
      if (btnSpan) {
        btnSpan.textContent = isAr ? `انشر الإعلان - ${fee} دينار` : `Publish Ad - ${fee} JOD`;
      }
    }

    const fCategory = document.getElementById("fCategory");
    const fAdDuration = document.getElementById("fAdDuration");
    if (fCategory) fCategory.addEventListener("change", updateWagePolicyBox);
    if (fAdDuration) fAdDuration.addEventListener("change", updateWagePolicyBox);
    setTimeout(updateWagePolicyBox, 100); // تهيئة أولية

    addFormEl.addEventListener("submit", async (e) => {
      e.preventDefault();

      const getVal = (id) => document.getElementById(id)?.value.trim() || "";
      const title = getVal("fTitle");
      const governorate = getVal("fGovernorate");
      const category = getVal("fCategory");
      const wage = getVal("fWage");
      const details = getVal("fDetails");
      const phone = getVal("fPhone");
      const errorEl = document.getElementById("addFormError");

      if (!title) { showFormError(errorEl, t("titleRequired")); return; }
      if (category !== "free" && category !== "ads") {
        if (!wage || parseFloat(wage) <= 0) { showFormError(errorEl, t("wageRequired")); return; }
      }
      if (!phone || !/^07\d{8}$/.test(phone)) { showFormError(errorEl, t("invalidPhone")); return; }
      if (!details) { showFormError(errorEl, t("fillAllFields")); return; }
      
      if (state.currentEditAdId) {
        await performSave();
      } else if (category === "free" || category === "ads") {
        await performSave();
      } else {
        if (elements.cliqModalOverlay) elements.cliqModalOverlay.classList.add("open");
      }
    });
  }

  const confirmCliqBtn = document.getElementById("confirmCliqBtn");
  if (confirmCliqBtn) {
    confirmCliqBtn.addEventListener("click", async () => {
      const receiptInput = document.getElementById("fReceipt");
      const errorEl = document.getElementById("cliqModalError");

      if (!receiptInput || !receiptInput.files || receiptInput.files.length === 0) {
        showFormError(errorEl, t("receiptRequired"));
        return;
      }

      try {
        await performSave();
        closeCliqModal();
      } catch (error) {}
    });
  }

  function updateSettingsPage() {
    if (!state.user) return;

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val;
    };

    setVal("settingsEmail", state.user.email || "");
    setVal("settingsUsername", state.user.username || "");

    const setCheck = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = val;
    };

    setCheck("togglePush", state.settings.pushNotifications);

    const govSelect = document.getElementById("settingsGov");
    if (govSelect) govSelect.value = state.settings.preferredGovernorate || "all";

    updateLanguageOptionsUI();
  }

  const saveAccountBtn = document.getElementById("saveAccountBtn");
  if (saveAccountBtn) {
    saveAccountBtn.addEventListener("click", () => {
      const newUsername = document.getElementById("settingsUsername")?.value.trim();
      if (newUsername && newUsername.length >= 3) {
        state.user.username = newUsername;
        localStorage.setItem("dj_user", JSON.stringify(state.user));
        updateDrawerUser();
        showToast(t("settingsSaved"), "success");
      } else {
        showToast(t("usernameMinLength"), "error");
      }
    });
  }

  const bindCheckSetting = (id, key) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", (e) => {
        state.settings[key] = e.target.checked;
        localStorage.setItem("dj_settings", JSON.stringify(state.settings));
      });
    }
  };

  bindCheckSetting("togglePush", "pushNotifications");

  const settingsGov = document.getElementById("settingsGov");
  if (settingsGov) {
    settingsGov.addEventListener("change", (e) => {
      state.settings.preferredGovernorate = e.target.value;
      localStorage.setItem("dj_settings", JSON.stringify(state.settings));
      showToast(t("preferredGovUpdated"), "success");
    });
  }

  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) logoutBtn.addEventListener("click", logout);

  function switchLanguage(lang) {
    state.lang = lang;
    localStorage.setItem("dj_lang", lang);

    const html = document.documentElement;
    if (lang === "ar") {
      html.setAttribute("dir", "rtl");
      html.setAttribute("lang", "ar");
    } else {
      html.setAttribute("dir", "ltr");
      html.setAttribute("lang", "en");
    }

    updateAllText();

    const langToggle = document.getElementById("langToggle");
    if (langToggle) langToggle.textContent = lang === "en" ? "عربي" : "EN";

    updateLanguageOptionsUI();
    populateFormSelects();

    const activeScreen = document.querySelector(".screen.active");
    if (activeScreen) {
      const screenName = activeScreen.id.replace("screen-", "");
      goToScreen(screenName);
    }

    showToast(lang === "ar" ? "تم تغيير اللغة إلى العربية" : "Language switched to English", "success");
  }

  function updateAllText() {
    // نص عادي (textContent - آمن من XSS)
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.dataset.i18n;
      if (i18n[state.lang] && i18n[state.lang][key]) {
        el.textContent = i18n[state.lang][key];
      }
    });

    // نص يحتوي على HTML (innerHTML - للعناصر الموثوقة فقط)
    document.querySelectorAll("[data-i18n-html]").forEach(el => {
      const key = el.dataset.i18nHtml;
      if (i18n[state.lang] && i18n[state.lang][key]) {
        el.innerHTML = i18n[state.lang][key];
      }
    });

    // ترجمة الـ placeholders
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
      const key = el.dataset.i18nPlaceholder;
      if (i18n[state.lang] && i18n[state.lang][key]) {
        el.placeholder = i18n[state.lang][key];
      }
    });

    const searchInput = document.getElementById("searchInput");
    if (searchInput) searchInput.placeholder = i18n[state.lang].searchPlaceholder;

    const titleInput = document.getElementById("fTitle");
    if (titleInput) titleInput.placeholder = state.lang === "ar" ? "مثال: مطلوب عامل بناء خبرة في مادبا" : "e.g.: Construction worker needed in Madaba";

    const detailsTextarea = document.getElementById("fDetails");
    if (detailsTextarea) detailsTextarea.placeholder = state.lang === "ar" ? "اكتب وصفك بالتفصيل هنا..." : "Write your description here...";

    const phoneInput = document.getElementById("fPhone");
    if (phoneInput) phoneInput.placeholder = "07X XXX XXXX";

    const usernameInput = document.getElementById("regUsername");
    if (usernameInput) usernameInput.placeholder = state.lang === "ar" ? "abu_mohammad" : "john_doe";

    document.querySelectorAll('input[type="password"]').forEach(input => {
      input.placeholder = "•••••••••";
    });
  }

  function updateLanguageOptionsUI() {
    const enOption = document.getElementById("langOptionEn");
    const arOption = document.getElementById("langOptionAr");

    if (enOption && arOption) {
      if (state.lang === "en") {
        enOption.classList.add("active");
        arOption.classList.remove("active");
      } else {
        enOption.classList.remove("active");
        arOption.classList.add("active");
      }
    }
  }

  const langToggle = document.getElementById("langToggle");
  if (langToggle) {
    langToggle.addEventListener("click", () => {
      switchLanguage(state.lang === "en" ? "ar" : "en");
    });
  }

  const langOptEn = document.getElementById("langOptionEn");
  const langOptAr = document.getElementById("langOptionAr");
  if (langOptEn) langOptEn.addEventListener("click", () => switchLanguage("en"));
  if (langOptAr) langOptAr.addEventListener("click", () => switchLanguage("ar"));

  let searchTimeout = null;
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        state.filters.query = e.target.value.trim();
        renderAds();
      }, 300);
    });
  }

  const typeChipRow = document.getElementById("typeChipRow");
  if (typeChipRow) {
    typeChipRow.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip[data-type]");
      if (!chip) return;

      typeChipRow.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");

      state.filters.type = chip.dataset.type;
      renderAds();
    });
  }

  const filterBtn = document.getElementById("filterBtn");
  const filterClose = document.getElementById("filterClose");
  const filterApplyBtn = document.getElementById("filterApplyBtn");
  const filterResetBtn = document.getElementById("filterResetBtn");

  if (filterBtn) {
    filterBtn.addEventListener("click", () => {
      populateFormSelects();
      if (elements.filterOverlay) elements.filterOverlay.classList.add("open");
    });
  }

  if (filterClose) {
    filterClose.addEventListener("click", () => {
      if (elements.filterOverlay) elements.filterOverlay.classList.remove("open");
    });
  }

  if (elements.filterOverlay) {
    elements.filterOverlay.addEventListener("click", (e) => {
      if (e.target === elements.filterOverlay) elements.filterOverlay.classList.remove("open");
    });
  }

  if (filterApplyBtn) {
    filterApplyBtn.addEventListener("click", () => {
      const activeCatChip = document.querySelector("#filterCategoryChips button.active");
      state.filters.category = activeCatChip ? activeCatChip.dataset.cat : "all";
      const fGov = document.getElementById("filterGovSelect");
      if (fGov) state.filters.governorate = fGov.value;

      if (elements.filterOverlay) elements.filterOverlay.classList.remove("open");
      renderAds();
      updateFilterButtonState();
      showToast(t("filtersApplied"), "success");
    });
  }

  function resetAllFilters() {
    state.filters = { type: "all", category: "all", governorate: "all", query: "" };

    if (searchInput) searchInput.value = "";
    document.querySelectorAll("#typeChipRow .chip").forEach(c => c.classList.remove("active"));
    const defaultChip = document.querySelector('#typeChipRow .chip[data-type="all"]');
    if (defaultChip) defaultChip.classList.add("active");
    document.querySelectorAll("#filterCategoryChips button").forEach(b => b.classList.remove("active"));
    const fGov = document.getElementById("filterGovSelect");
    if (fGov) fGov.value = "all";

    if (elements.filterOverlay) elements.filterOverlay.classList.remove("open");
    renderAds();
    updateFilterButtonState();
    showToast(t("filtersReset"), "info");
  }

  if (filterResetBtn) {
    filterResetBtn.addEventListener("click", resetAllFilters);
  }

  const resetFiltersEmptyBtn = document.getElementById("resetFiltersEmptyBtn");
  if (resetFiltersEmptyBtn) {
    resetFiltersEmptyBtn.addEventListener("click", resetAllFilters);
  }

  function updateFilterButtonState() {
    if (!filterBtn) return;
    const hasActiveFilters = 
      state.filters.category !== "all" || 
      state.filters.governorate !== "all" ||
      state.filters.query !== "" ||
      state.filters.type !== "all";

    if (hasActiveFilters) filterBtn.classList.add("has-active");
    else filterBtn.classList.remove("has-active");
  }

  function updateActiveFiltersDisplay() {
    const container = document.getElementById("activeFilters");
    if (!container) return;
    const tags = [];

    if (state.filters.query) {
      tags.push(`
        <span class="filter-tag">
          <i class="fa-solid fa-magnifying-glass"></i>
          ${escapeHtml(state.filters.query)}
          <i class="fa-solid fa-xmark" data-clear-filter="query"></i>
        </span>
      `);
    }

    if (state.filters.type !== "all") {
      const typeName = state.filters.type === "daily" ? t("dailyJob") :
                       state.filters.type === "fulltime" ? t("fullTime") :
                       state.filters.type === "ads" ? t("announcements") :
                       state.filters.type === "services" ? t("services") :
                       state.filters.type === "used" ? t("usedGoods") :
                       state.filters.type === "free" ? t("freebies") : state.filters.type;
      tags.push(`<span class="filter-tag">${typeName}<i class="fa-solid fa-xmark" data-clear-filter="type"></i></span>`);
    }

    if (state.filters.category !== "all") {
      const catName = getCategoryName(state.filters.category, state.lang);
      tags.push(`<span class="filter-tag">${catName}<i class="fa-solid fa-xmark" data-clear-filter="category"></i></span>`);
    }

    if (state.filters.governorate !== "all") {
      const govName = GOV_MAP[state.filters.governorate] ? GOV_MAP[state.filters.governorate][state.lang] : state.filters.governorate;
      tags.push(`
        <span class="filter-tag">
          <i class="fa-solid fa-location-dot"></i>
          ${govName}
          <i class="fa-solid fa-xmark" data-clear-filter="governorate"></i>
        </span>
      `);
    }

    container.innerHTML = tags.join("");

    container.querySelectorAll("[data-clear-filter]").forEach(btn => {
      btn.addEventListener("click", () => {
        const filterType = btn.dataset.clearFilter;
        if (filterType === "query") { state.filters.query = ""; if (searchInput) searchInput.value = ""; }
        else if (filterType === "type") { state.filters.type = "all"; }
        else if (filterType === "category") { state.filters.category = "all"; }
        else if (filterType === "governorate") { state.filters.governorate = "all"; }
        renderAds();
        updateFilterButtonState();
      });
    });
  }

  let toastTimer = null;
  function showToast(message, kind = "info") {
    clearTimeout(toastTimer);
    const toastEl = elements.toast;
    if (!toastEl) return;

    const icons = {
      success: "fa-circle-check",
      error: "fa-circle-exclamation",
      info: "fa-circle-info",
      warning: "fa-triangle-exclamation"
    };

    toastEl.className = `toast toast-${kind}`;
    toastEl.innerHTML = `<i class="fa-solid ${icons[kind] || icons.info}"></i><span>${escapeHtml(message)}</span>`;
    toastEl.classList.add("show");
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), 2800);
  }

  function t(key) {
    return i18n[state.lang][key] || key;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function formatRelative(date) {
    const mins = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
    if (mins < 60) return `${mins} ${t("minsAgo")}`;
    else if (mins < 1440) return `${Math.round(mins / 60)} ${t("hoursAgo")}`;
    else return `${Math.round(mins / 1440)} ${t("daysAgo")}`;
  }

  function showFormError(el, msg) {
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
    setTimeout(() => el.classList.add("hidden"), 4000);
  }

  function handleImagePreview(inputId, btnId, previewListId) {
    const fileInput = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    const previewList = document.getElementById(previewListId);

    if (btn && fileInput) {
      btn.addEventListener("click", () => fileInput.click());
    }

    if (fileInput && previewList) {
      fileInput.addEventListener("change", () => {
        previewList.innerHTML = "";
        const files = Array.from(fileInput.files);
        files.forEach((file) => {
          if (!file.type.startsWith("image/")) return;
          const reader = new FileReader();
          reader.onload = (e) => {
            const item = document.createElement("div");
            item.className = "image-preview-item";
            item.innerHTML = `
              <img src="${e.target.result}" alt="Preview">
              <span class="image-preview-remove"><i class="fa-solid fa-xmark"></i></span>
            `;
            item.querySelector(".image-preview-remove").addEventListener("click", (ev) => {
              ev.stopPropagation();
              item.remove();
            });
            previewList.appendChild(item);
          };
          reader.readAsDataURL(file);
        });
      });
    }
  }

  async function init() {
    const savedUser = localStorage.getItem("dj_user");
    if (savedUser) {
      try {
        state.user = JSON.parse(savedUser);
        state.isAuthenticated = true;
        
        // Always ensure role is fetched if missing
        if (!state.user.role) {
            const token = localStorage.getItem("dj_token");
            if (token) {
                fetch(`${BASE_URL}/users/${state.user.id}/`, {
                    headers: { 'Authorization': 'Token ' + token }
                }).then(r => r.json()).then(data => {
                    if (data && data.role) {
                        state.user.role = data.role;
                        localStorage.setItem("dj_user", JSON.stringify(state.user));
                        updateDrawerUser();
                    }
                }).catch(e => console.error(e));
            }
        }
        
      } catch (e) {
        localStorage.removeItem("dj_user");
      }
    }

    const savedSettings = localStorage.getItem("dj_settings");
    if (savedSettings) {
      try {
        state.settings = { ...state.settings, ...JSON.parse(savedSettings) };
      } catch (e) {}
    }

    const html = document.documentElement;
    if (state.lang === "ar") {
      html.setAttribute("dir", "rtl");
      html.setAttribute("lang", "ar");
    } else {
      html.setAttribute("dir", "ltr");
      html.setAttribute("lang", "en");
    }

    const langToggleBtn = document.getElementById("langToggle");
    if (langToggleBtn) langToggleBtn.textContent = state.lang === "en" ? "عربي" : "EN";

    populateFormSelects();
    handleImagePreview("fImages", "imageUploadBtn", "imagePreviewList");
    handleImagePreview("fReceipt", "receiptUploadBtn", "receiptPreviewList");

    updateAllText();
    updateDrawerUser();
    updateNotificationDot();

    // تحميل فوري للإعلانات المحفوظة محلياً لسرعة العرض الفورية (0.01 ثانية)
    try {
      const cached = localStorage.getItem("dj_cached_ads");
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) {
          ads = parsed.map(a => ({
            ...a,
            createdAt: new Date(a.createdAt),
            mine: !!(state.user && (a.user_email === state.user.email || a.mine))
          }));
          renderAds();
        }
      }
    } catch (e) {}

    // تحميل فوري للإشعارات المحفوظة محلياً
    try {
      const cachedNotifs = localStorage.getItem("dj_cached_notifications");
      if (cachedNotifs) {
        state.notifications = JSON.parse(cachedNotifs);
        renderNotifications();
        updateNotificationDot();
      }
    } catch (e) {}

    // تعديل: استعادة الشاشة السابقة بدلاً من الذهاب إلى الرئيسية دائماً
    const lastScreen = sessionStorage.getItem("dj_lastScreen") || "home";
    if (lastScreen !== "details" && lastScreen !== "edit") {
      goToScreen(lastScreen);
    } else {
      // نعرض شاشة فارغة مؤقتاً أو تحميل حتى تأتي الإعلانات
      document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
      const targetScreen = document.getElementById("screen-" + lastScreen);
      if (targetScreen) targetScreen.classList.add("active");
    }

    loadAdsFromAPI().then(() => {
      if (lastScreen === "details") {
        const adId = sessionStorage.getItem("dj_lastAdId");
        if (adId && ads.some(a => a.id === adId)) {
          state.currentAdId = adId;
          renderDetails(adId);
        } else {
          goToScreen("home");
        }
      } else if (lastScreen === "add") {
        const editId = sessionStorage.getItem("dj_lastEditAdId");
        if (editId && ads.some(a => a.id === editId)) {
          // كنا في وضع التعديل
          openEdit(editId); 
        } else {
          // إضافة عادية، لا نحتاج لفعل شيء إضافي لأن goToScreen("add") أظهرت الشاشة
        }
      }
    });

    fetchNotifications();
    startSilentPolling(); // تعديل 3: تحديث تلقائي كل 45 ثانية

    // استعادة حالة التحقق من البريد الإلكتروني
    if (state.tempEmail && !state.isAuthenticated) {
      document.getElementById("authModal").classList.add("active");
      document.querySelectorAll('.auth-step').forEach(s => s.classList.add('hidden'));
      document.getElementById('authStepVerify').classList.remove('hidden');
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function setupEnterToNext(containerId, submitBtnId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const inputs = Array.from(container.querySelectorAll('input:not([type="hidden"]):not([disabled])'));

    inputs.forEach((input, index) => {
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          if (index < inputs.length - 1) {
            inputs[index + 1].focus();
          } else {
            const submitBtn = document.getElementById(submitBtnId);
            if (submitBtn) submitBtn.click();
          }
        }
      });
    });
  }

  setupEnterToNext('authStepLogin', 'loginSubmitBtn');
  setupEnterToNext('authStepRegister', 'registerSubmitBtn');
  setupEnterToNext('authStepForgot', 'forgotSubmitBtn');
  setupEnterToNext('authStepReset', 'resetSubmitBtn');

  document.addEventListener('click', function (e) {
    const toggleBtn = e.target.closest('.toggle-password');
    if (!toggleBtn) return;

    const wrapper = toggleBtn.closest('.password-wrapper');
    if (!wrapper) return;
    
    const passInput = wrapper.querySelector('input');
    if (!passInput) return;

    const isPassword = passInput.getAttribute('type') === 'password';
    passInput.setAttribute('type', isPassword ? 'text' : 'password');

    toggleBtn.classList.toggle('fa-eye-slash');
    toggleBtn.classList.toggle('fa-eye');
    passInput.focus();
  });

  // 1. زر تأكيد البريد بعد التسجيل (OTP)
  const verifySubmitBtn = document.getElementById("verifySubmitBtn");
  if(verifySubmitBtn) {
    verifySubmitBtn.addEventListener("click", async () => {
      const otp = document.getElementById("verifyOtp").value.trim();
      const errorEl = document.getElementById("verifyError");
      
      if(otp.length !== 6) { showFormError(errorEl, "الرمز يجب أن يكون 6 أرقام"); return; }
      
      const originalText = verifySubmitBtn.innerHTML;
      try {
        verifySubmitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        verifySubmitBtn.disabled = true;
        
        await Api.verifyEmail(state.tempEmail, otp);
        
        const result = await Api.login(state.tempEmail, state.tempPassword);
        state.isAuthenticated = true;
        state.user = result.user;
        localStorage.setItem("dj_user", JSON.stringify(state.user));
        localStorage.setItem("dj_token", result.token);
        
        sessionStorage.removeItem('dj_tempEmail');
        sessionStorage.removeItem('dj_tempPassword');
        state.tempEmail = null;
        state.tempPassword = null;
        
        closeAuth();
        updateDrawerUser();
        showToast("تم تفعيل حسابك بنجاح!", "success");
        fetchNotifications();
        
      } catch (error) {
        showFormError(errorEl, error.message);
      } finally {
        verifySubmitBtn.innerHTML = originalText;
        verifySubmitBtn.disabled = false;
      }
    });
  }

  // 2. زر نسيت كلمة المرور
  const forgotPasswordBtn = document.getElementById("forgotPasswordBtn");
  if(forgotPasswordBtn) {
    forgotPasswordBtn.addEventListener("click", (e) => {
      e.preventDefault();
      showAuthStep('authStepForgot');
    });
  }

  // --- DELETE AD ---
  const deleteAdBtn = document.getElementById("deleteAdBtn");
  if (deleteAdBtn) {
    deleteAdBtn.addEventListener("click", async () => {
      if (!confirm(t("confirmDeleteAd"))) return;
      try {
        const token = localStorage.getItem("dj_token");
        await Api.deleteAd(state.currentAdId, token);
        ads = ads.filter(a => a.id !== state.currentAdId);
        renderAds();
        showToast("تم حذف الإعلان بنجاح!", "success");
        goToScreen("home");
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // --- DELETE ACCOUNT --- (تم نقله للأسفل مع الإصلاحات الكاملة)


  const backToLoginBtn = document.getElementById("backToLoginBtn");
  if(backToLoginBtn) {
    backToLoginBtn.addEventListener("click", (e) => {
      e.preventDefault();
      showLoginStep();
    });
  }

  // 3. زر إرسال الإيميل لطلب استعادة كلمة المرور
  const forgotSubmitBtn = document.getElementById("forgotSubmitBtn");
  if(forgotSubmitBtn) {
    forgotSubmitBtn.addEventListener("click", async () => {
      const email = document.getElementById("forgotEmail").value.trim();
      const errorEl = document.getElementById("forgotError");
      
      if(!isValidEmail(email)) { showFormError(errorEl, "بريد إلكتروني غير صالح"); return; }
      
      const originalText = forgotSubmitBtn.innerHTML;
      try {
        forgotSubmitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        forgotSubmitBtn.disabled = true;
        
        await Api.requestPasswordReset(email);
        
        state.resetUserEmail = email; // تخزين الإيميل للمرحلة القادمة
        showToast("تم إرسال رمز التحقق إلى بريدك!", "success");
        
        // الانتقال لشاشة إدخال الرمز
        showAuthStep('authStepReset');
        
      } catch (error) {
        showFormError(errorEl, error.message);
      } finally {
        forgotSubmitBtn.innerHTML = originalText;
        forgotSubmitBtn.disabled = false;
      }
    });
  }

  // 4. زر حفظ كلمة المرور الجديدة باستخدام OTP
  const resetSubmitBtn = document.getElementById("resetSubmitBtn");
  if(resetSubmitBtn) {
    resetSubmitBtn.addEventListener("click", async () => {
      const otp = document.getElementById("resetOtp").value.trim();
      const newPass = document.getElementById("resetNewPassword").value;
      const errorEl = document.getElementById("resetError");
      
      if(otp.length !== 6) { showFormError(errorEl, "الرمز يجب أن يكون 6 أرقام"); return; }
      if(newPass.length < 6) { showFormError(errorEl, "كلمة المرور يجب أن تكون 6 أحرف على الأقل"); return; }
      
      const originalText = resetSubmitBtn.innerHTML;
      try {
        resetSubmitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        resetSubmitBtn.disabled = true;
        
        await Api.confirmPasswordReset(state.resetUserEmail, otp, newPass);
        
        showToast("تم تغيير كلمة المرور بنجاح!", "success");
        
        // مسح الحقول والعودة لتسجيل الدخول
        document.getElementById("resetOtp").value = "";
        document.getElementById("resetNewPassword").value = "";
        document.getElementById("forgotEmail").value = "";
        state.resetUserEmail = "";
        
        showLoginStep();
        
      } catch (error) {
        showFormError(errorEl, error.message);
      } finally {
        resetSubmitBtn.innerHTML = originalText;
        resetSubmitBtn.disabled = false;
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // اقتراح #4: مؤقت OTP + زر إعادة إرسال في شاشة التحقق
  // ══════════════════════════════════════════════════════════════════
  let _otpTimer = null;
  function startOtpTimer() {
    let secs = 60;
    const countEl = document.getElementById('otpTimerCount');
    const textEl  = document.getElementById('otpTimerText');
    const suffEl  = document.getElementById('otpTimerSuffix');
    const resendBtn = document.getElementById('resendOtpBtn');
    if (!countEl) return;
    if (_otpTimer) clearInterval(_otpTimer);
    // إظهار المؤقت وإخفاء زر الإعادة
    countEl.textContent = secs;
    if (textEl) { textEl.style.display = ''; textEl.textContent = 'إعادة إرسال الرمز خلال '; }
    if (suffEl) suffEl.style.display = '';
    if (resendBtn) resendBtn.classList.add('hidden');

    _otpTimer = setInterval(() => {
      secs--;
      if (countEl) countEl.textContent = secs;
      if (secs <= 0) {
        clearInterval(_otpTimer);
        if (textEl) textEl.style.display = 'none';
        if (suffEl) suffEl.style.display = 'none';
        if (countEl) countEl.style.display = 'none';
        if (resendBtn) resendBtn.classList.remove('hidden');
      }
    }, 1000);
  }

  // ابدأ المؤقت عند عرض شاشة التحقق
  const origShowVerify = () => {
    document.querySelectorAll('.auth-step').forEach(s => s.classList.add('hidden'));
    const verifyStep = document.getElementById('authStepVerify');
    if (verifyStep) {
      verifyStep.classList.remove('hidden');
      const countEl = document.getElementById('otpTimerCount');
      if (countEl) countEl.style.display = '';
      startOtpTimer();
    }
  };

  // اعتراض الكود الأصلي في registerSubmitBtn لاستدعاء startOtpTimer
  const _origRegisterSuccess = window._registerSuccess;
  document.getElementById('registerSubmitBtn')?.addEventListener('click', () => {
    // المؤقت يبدأ عند انتقال شاشة التسجيل لشاشة التحقق
    setTimeout(() => {
      if (!document.getElementById('authStepVerify')?.classList.contains('hidden')) {
        startOtpTimer();
      }
    }, 300);
  });

  // زر إعادة الإرسال
  const resendOtpBtn = document.getElementById('resendOtpBtn');
  if (resendOtpBtn) {
    resendOtpBtn.addEventListener('click', async () => {
      if (!state.tempEmail) return;
      resendOtpBtn.disabled = true;
      try {
        await Api.resendOtp(state.tempEmail);
        showToast('تم إعادة إرسال رمز التحقق!', 'success');
        startOtpTimer();
      } catch(e) {
        showToast(e.message, 'error');
      } finally {
        resendOtpBtn.disabled = false;
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // اقتراح #1: مؤشر قوة كلمة المرور في التسجيل
  // ══════════════════════════════════════════════════════════════════
  const regPassInput = document.getElementById('regPassword');
  if (regPassInput) {
    regPassInput.addEventListener('input', () => {
      const pass = regPassInput.value;
      const bars = [
        document.getElementById('pBar1'),
        document.getElementById('pBar2'),
        document.getElementById('pBar3'),
        document.getElementById('pBar4'),
      ];
      const label = document.getElementById('passwordStrengthLabel');
      if (!bars[0]) return;

      // حساب القوة
      let score = 0;
      if (pass.length >= 6)  score++;
      if (pass.length >= 10) score++;
      if (/[A-Z]/.test(pass) && /[a-z]/.test(pass)) score++;
      if (/[0-9]/.test(pass)) score++;
      if (/[^A-Za-z0-9]/.test(pass)) score = Math.min(4, score + 1);

      const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e'];
      const labels = ['ضعيفة جداً', 'ضعيفة', 'متوسطة', 'قوية'];
      bars.forEach((b, i) => {
        b.style.background = i < score ? colors[score - 1] : '#e5e7eb';
      });
      if (label) {
        label.textContent = pass.length > 0 ? labels[Math.min(score - 1, 3)] : '';
        label.style.color = score > 0 ? colors[score - 1] : '#999';
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // اقتراح #5: صفحة القسائم على الموقع
  // ══════════════════════════════════════════════════════════════════
  async function loadCouponsScreen() {
    const token = localStorage.getItem('dj_token');
    const user  = state.user;
    if (!token || !user) return;

    // بطاقة الإحالة
    const referralCard = document.getElementById('referralCard');
    const referralCodeEl = document.getElementById('myReferralCode');
    if (referralCard && user.referral_code) {
      referralCard.classList.remove('hidden');
      if (referralCodeEl) referralCodeEl.textContent = user.referral_code;
    } else if (referralCard) {
      // محاولة جلب كود الإحالة من localStorage
      const savedUser = JSON.parse(localStorage.getItem('dj_user') || '{}');
      if (savedUser.referral_code) {
        referralCard.classList.remove('hidden');
        if (referralCodeEl) referralCodeEl.textContent = savedUser.referral_code;
      }
    }

    // زر نسخ كود الإحالة (اقتراح #5)
    const copyRefBtn = document.getElementById('copyReferralBtn');
    if (copyRefBtn) {
      copyRefBtn.onclick = () => {
        const code = referralCodeEl?.textContent || '';
        if (!code || code === '---') return;
        navigator.clipboard.writeText(code).then(() => showToast('تم نسخ كود الإحالة!', 'success'));
      };
    }
    const shareRefBtn = document.getElementById('shareReferralBtn');
    if (shareRefBtn) {
      shareRefBtn.onclick = () => {
        const code = referralCodeEl?.textContent || '';
        const msg = t('shareMsg').replace('{code}', code);
        navigator.clipboard.writeText(msg).then(() => showToast(t('shareSuccessToast'), 'success'));
      };
    }

    // القسائم النشطة
    const activeList   = document.getElementById('activeCouponsList');
    const activeEmpty  = document.getElementById('activeCouponsEmpty');
    const historyList  = document.getElementById('historyCouponsList');
    const historyEmpty = document.getElementById('historyCouponsEmpty');
    if (!activeList) return;
    activeList.innerHTML = '<div style="text-align:center;padding:20px;color:#999;"><i class="fa-solid fa-spinner fa-spin"></i></div>';
    if (historyList) historyList.innerHTML = '';

    try {
      const coupons = await Api.getCoupons(token);
      const now = new Date();

      const active  = coupons.filter(c => !c.is_used && !c.is_expired && (!c.expires_at || new Date(c.expires_at) > now));
      const history = coupons.filter(c =>  c.is_used ||  c.is_expired);

      // عرض النشطة
      activeList.innerHTML = '';
      if (active.length === 0) {
        if (activeEmpty) activeEmpty.classList.remove('hidden');
      } else {
        if (activeEmpty) activeEmpty.classList.add('hidden');
        active.forEach(c => activeList.insertAdjacentHTML('beforeend', renderCouponCard(c, true)));
      }

      // عرض السجل
      if (historyList) {
        historyList.innerHTML = '';
        if (history.length === 0) {
          if (historyEmpty) historyEmpty.classList.remove('hidden');
        } else {
          if (historyEmpty) historyEmpty.classList.add('hidden');
          history.forEach(c => historyList.insertAdjacentHTML('beforeend', renderCouponCard(c, false)));
        }
      }

      // أحداث نسخ الأكواد
      document.querySelectorAll('.coupon-copy-btn').forEach(btn => {
        btn.onclick = () => {
          const code = btn.dataset.code;
          navigator.clipboard.writeText(code).then(() => showToast('تم نسخ كود القسيمة!', 'success'));
        };
      });
    } catch(e) {
      if (activeList) activeList.innerHTML = '<p style="text-align:center;color:#ef4444;">فشل تحميل القسائم</p>';
    }
  }

  function renderCouponCard(coupon, isActive) {
    const expiresAt = coupon.expires_at ? new Date(coupon.expires_at) : null;
    const dateStr = expiresAt
      ? `${expiresAt.getFullYear()}-${String(expiresAt.getMonth()+1).padStart(2,'0')}-${String(expiresAt.getDate()).padStart(2,'0')}`
      : '';
    const isUsed = coupon.is_used;
    const barColor = isActive ? '#FF6A00' : (isUsed ? '#22c55e' : '#9ca3af');
    const badgeColor = isActive ? '#FFF0E4' : (isUsed ? 'rgba(34,197,94,0.1)' : 'rgba(156,163,175,0.1)');
    const badgeTextColor = isActive ? '#FF6A00' : (isUsed ? '#22c55e' : '#9ca3af');
    const badgeLabel = isActive ? 'نشط' : (isUsed ? 'مستخدم' : 'منتهي');

    return `
    <div style="background:white; border-radius:12px; border:1px solid ${isActive ? 'rgba(255,106,0,0.3)' : '#ECEDF3'}; margin-bottom:12px; overflow:hidden; display:flex;">
      <div style="width:10px; background:${barColor}; flex-shrink:0;"></div>
      <div style="padding:16px; flex:1; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <span style="font-weight:bold; color:#151A2E;">إعلان مجاني</span>
            <span style="background:${badgeColor}; color:${badgeTextColor}; font-size:10px; font-weight:bold; padding:2px 8px; border-radius:20px;">${badgeLabel}</span>
          </div>
          <div style="font-size:12px; color:#7A8099; margin-bottom:3px;">الكود: <strong style="color:#151A2E;">${coupon.code}</strong></div>
          ${isActive && dateStr ? `<div style="font-size:11px; color:#ef4444; font-weight:500;">ينتهي في: ${dateStr}</div>` : ''}
          ${isUsed && coupon.used_at ? `<div style="font-size:11px; color:#7A8099;">استُخدم في: ${coupon.used_at.split('T')[0]}</div>` : ''}
          ${!isActive && !isUsed && dateStr ? `<div style="font-size:11px; color:#9ca3af;">انتهى في: ${dateStr}</div>` : ''}
        </div>
        ${isActive ? `<button class="coupon-copy-btn" data-code="${coupon.code}" style="background:#FF6A00; color:white; border:none; border-radius:8px; padding:8px 12px; cursor:pointer; font-size:13px;"><i class="fa-solid fa-copy"></i></button>` : ''}
      </div>
    </div>`;
  }

  // زر Refresh في صفحة القسائم
  const refreshCouponsBtn = document.getElementById('refreshCouponsBtn');
  if (refreshCouponsBtn) {
    refreshCouponsBtn.addEventListener('click', loadCouponsScreen);
  }

  // ══════════════════════════════════════════════════════════════════
  // اقتراح #2: Rate limiting — عرض رسالة واضحة عند OTP throttle
  // (يُعالج تلقائياً من Api.resendOtp الذي يُرجع error.message من السيرفر)
  // ══════════════════════════════════════════════════════════════════

  // ══════════════════════════════════════════════════════════════════
  // إصلاح حذف الحساب — مسح كامل للبيانات
  // ══════════════════════════════════════════════════════════════════
  const deleteAccountBtn = document.getElementById("deleteAccountBtn");
  if (deleteAccountBtn) {
    deleteAccountBtn.addEventListener("click", async () => {
      if (!state.isAuthenticated || !state.user) {
        showToast("يجب تسجيل الدخول أولاً.", "error");
        return;
      }
      const userId = state.user?.id;
      if (!confirm(t("confirmDeleteAccount"))) return;
      try {
        const token = localStorage.getItem("dj_token");
        await Api.deleteAccount(userId, token);

        // مسح كامل للبيانات المحلية
        localStorage.removeItem("dj_user");
        localStorage.removeItem("dj_token");
        localStorage.removeItem("dj_favorites");
        sessionStorage.clear();

        state.isAuthenticated = false;
        state.user = null;
        state.favorites = new Set();
        updateDrawerUser();

        showToast("تم حذف حسابك بنجاح. نتمنى أن نراك مجدداً!", "success");
        goToScreen("home");
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

})();

function openContactModal() {
    document.getElementById('contact-modal').style.display = 'block';
    closeMenu();
}

async function submitContactForm(e) {
    e.preventDefault();
    const btn = document.getElementById('contact-submit-btn');
    btn.disabled = true;
    btn.innerText = 'جاري الإرسال...';
    
    const data = {
        name: document.getElementById('contact-name').value,
        email: document.getElementById('contact-email').value,
        subject: document.getElementById('contact-subject').value,
        message: document.getElementById('contact-message').value
    };
    
    try {
        const response = await fetch(API_BASE_URL + 'contact/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            showToast('تم إرسال رسالتك بنجاح', 'success');
            showScreen('home');
            document.getElementById('contact-form').reset();
        } else {
            showToast('فشل إرسال الرسالة', 'error');
        }
    } catch (error) {
        showToast('خطأ في الاتصال بالسيرفر', 'error');
    } finally {
        btn.disabled = false;
        btn.innerText = 'إرسال';
    }
}
