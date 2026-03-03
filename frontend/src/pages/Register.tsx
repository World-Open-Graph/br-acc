import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import {
  registerSchema,
  type RegisterFormValues,
  getAuthErrorMessage,
} from "@/lib/validations/auth";
import { useAuthStore } from "@/stores/auth";

import styles from "./Register.module.css";

export function Register() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { register: registerUser, loading, error } = useAuthStore();

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
      inviteCode: "",
    },
    mode: "onTouched",
  });

  const onSubmit = form.handleSubmit(async (data) => {
    await registerUser(data.email, data.password, data.inviteCode);
    if (useAuthStore.getState().token) {
      navigate("/app");
    }
  });

  const { errors } = form.formState;

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>{t("auth.registerTitle")}</h1>
          <p className={styles.subtitle}>{t("auth.loginSubtitle")}</p>
        </div>

        <form className={styles.form} onSubmit={onSubmit}>
          {error && <div className={styles.error}>{t(error)}</div>}

          <div className={styles.field}>
            <label className={styles.label} htmlFor="reg-email">
              {t("auth.email")}
            </label>
            <input
              id="reg-email"
              className={styles.input}
              type="email"
              autoComplete="email"
              aria-invalid={Boolean(errors.email)}
              aria-describedby={errors.email ? "reg-email-error" : undefined}
              {...form.register("email")}
            />
            {errors.email?.message && (
              <span id="reg-email-error" className={styles.fieldError} role="alert">
                {getAuthErrorMessage(errors.email.message, t)}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="reg-password">
              {t("auth.password")}
            </label>
            <input
              id="reg-password"
              className={styles.input}
              type="password"
              autoComplete="new-password"
              aria-invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? "reg-password-error" : undefined}
              {...form.register("password")}
            />
            {errors.password?.message && (
              <span id="reg-password-error" className={styles.fieldError} role="alert">
                {getAuthErrorMessage(errors.password.message, t)}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="reg-confirm-password">
              {t("auth.confirmPassword")}
            </label>
            <input
              id="reg-confirm-password"
              className={styles.input}
              type="password"
              autoComplete="new-password"
              aria-invalid={Boolean(errors.confirmPassword)}
              aria-describedby={errors.confirmPassword ? "reg-confirm-password-error" : undefined}
              {...form.register("confirmPassword")}
            />
            {errors.confirmPassword?.message && (
              <span id="reg-confirm-password-error" className={styles.fieldError} role="alert">
                {getAuthErrorMessage(errors.confirmPassword.message, t)}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="reg-invite">
              {t("auth.inviteCode")}
            </label>
            <input
              id="reg-invite"
              className={styles.input}
              type="text"
              autoComplete="off"
              aria-invalid={Boolean(errors.inviteCode)}
              aria-describedby={errors.inviteCode ? "reg-invite-error" : undefined}
              {...form.register("inviteCode")}
            />
            {errors.inviteCode?.message && (
              <span id="reg-invite-error" className={styles.fieldError} role="alert">
                {getAuthErrorMessage(errors.inviteCode.message, t)}
              </span>
            )}
          </div>

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={form.formState.isSubmitting || loading}
          >
            {loading ? t("common.loading") : t("auth.register")}
          </button>
        </form>

        <div className={styles.footer}>
          <Link to="/login" className={styles.switchLink}>
            {t("auth.switchToLogin")}
          </Link>
        </div>
      </div>
    </div>
  );
}
