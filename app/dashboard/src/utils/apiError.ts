import i18n from "locales/i18n";

type ApiErrorDetail = {
  code?: unknown;
  error_code?: unknown;
  message_fa?: unknown;
  request_id?: unknown;
  field?: unknown;
  fields?: unknown;
  correlation_id?: unknown;
  operation_id?: unknown;
};

const safeIdentifier = (value: unknown): string | null => {
  if (typeof value !== "string" || !/^[A-Za-z0-9_.:-]{1,128}$/.test(value)) return null;
  return value;
};

export const localizedApiError = (error: unknown): string => {
  const candidate = error as any;
  const detail = (candidate?.data?.detail || candidate?.response?._data?.detail) as ApiErrorDetail | string | undefined;
  const status = Number(candidate?.status || candidate?.statusCode || candidate?.response?.status || 0);
  if (detail && typeof detail === "object") {
    if (typeof detail.message_fa === "string" && detail.message_fa.trim()) {
      return detail.message_fa;
    }
    const code = safeIdentifier(detail.error_code) || safeIdentifier(detail.code);
    if (code) {
      const key = `errors.codes.${code}`;
      const translated = i18n.t(key, { defaultValue: "" });
      if (translated && translated !== key) return translated;
      return i18n.t("errors.unknownCode", { code });
    }
    const correlation = safeIdentifier(detail.request_id) || safeIdentifier(detail.correlation_id) || safeIdentifier(detail.operation_id);
    if (correlation) return i18n.t("errors.fallbackWithReference", { reference: correlation });
  }
  if (typeof detail === "string" && /[\u0600-\u06ff]/.test(detail)) return detail;
  return status ? i18n.t("errors.fallbackWithStatus", { status }) : i18n.t("errors.fallback");
};
