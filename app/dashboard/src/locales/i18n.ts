import { joinPaths } from "@remix-run/router";

import fa from "date-fns/locale/fa-IR";
import dayjs from "dayjs";
import "dayjs/locale/fa";
import i18n from "i18next";
import HttpApi from "i18next-http-backend";
import { registerLocale } from "react-datepicker";
import { initReactI18next } from "react-i18next";

declare module "i18next" {
    interface CustomTypeOptions {
        returnNull: false;
    }
}

const syncDocumentLanguage = () => {
    document.documentElement.lang = "fa";
    document.documentElement.dir = "rtl";
};

i18n
    .use(initReactI18next)
    .use(HttpApi)
    .init(
        {
            debug: import.meta.env.NODE_ENV === "development",
            returnNull: false,
            lng: "fa",
            supportedLngs: ["fa"],
            fallbackLng: "fa",
            interpolation: {
                escapeValue: false,
            },
            react: {
                useSuspense: false,
            },
            load: "languageOnly",
            backend: {
                loadPath: `${joinPaths([
                    import.meta.env.BASE_URL,
                    `statics/locales/{{lng}}.json`,
                ])}?v=${__LOCALE_BUILD_ID__}`,
            },
        },
        function () {
            dayjs.locale("fa");
            syncDocumentLanguage();
        }
    );

i18n.on("languageChanged", () => {
    dayjs.locale("fa");
    syncDocumentLanguage();
});

// DataPicker
registerLocale("fa", fa);

export default i18n;
