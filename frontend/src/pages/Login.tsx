import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import {
  loginSchema,
  type LoginFormValues,
  getAuthErrorMessage,
} from "@/lib/validations/auth";
import { useAuthStore } from "@/stores/auth";

import styles from "./Login.module.css";

export function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, loading, error } = useAuthStore();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
    mode: "onTouched",
  });

  const onSubmit = form.handleSubmit(async (data) => {
    await login(data.email, data.password);
    if (useAuthStore.getState().token) {
      navigate("/app");
    }
  });

  const { errors } = form.formState;

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>{t("auth.loginTitle")}</h1>
          <p className={styles.subtitle}>{t("auth.loginSubtitle")}</p>
        </div>

        <form className={styles.form} onSubmit={onSubmit}>
          {error && <div className={styles.error}>{t(error)}</div>}

          <div className={styles.field}>
            <label className={styles.label} htmlFor="email">
              {t("auth.email")}
            </label>
            <input
              id="email"
              className={styles.input}
              type="email"
              autoComplete="email"
              aria-invalid={Boolean(errors.email)}
              aria-describedby={errors.email ? "email-error" : undefined}
              {...form.register("email")}
            />
            {errors.email?.message && (
              <span id="email-error" className={styles.fieldError} role="alert">
                {getAuthErrorMessage(errors.email.message, t)}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="password">
              {t("auth.password")}
            </label>
            <input
              id="password"
              className={styles.input}
              type="password"
              autoComplete="current-password"
              aria-invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? "password-error" : undefined}
              {...form.register("password")}
            />
            {errors.password?.message && (
              <span id="password-error" className={styles.fieldError} role="alert">
                {getAuthErrorMessage(errors.password.message, t)}
              </span>
            )}
          </div>

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={form.formState.isSubmitting || loading}
          >
            {loading ? t("common.loading") : t("auth.login")}
          </button>
        </form>

        <div className={styles.footer}>
          <Link to="/register" className={styles.switchLink}>
            {t("auth.switchToRegister")}
          </Link>
        </div>
      </div>
    </div>
  );
}
