import { useMemo, useState } from "react";
import { AxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { referenceApi, ticketApi } from "../api/services";
import { useAuth } from "../components/AuthProvider";
import { categoryLabel, priorityLabel } from "../i18n/fr";
import type { TicketCategory, TicketPriority } from "../types/api";

interface CreateTicketForm {
  title: string;
  description: string;
  category: TicketCategory;
  priority: TicketPriority;
  target_department_id: number;
  assignee_id: string;
  is_department_broadcast: boolean;
}

export function TicketsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [formMessage, setFormMessage] = useState<string | null>(null);

  const departments = useQuery({
    queryKey: ["departments"],
    queryFn: () => referenceApi.departments()
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => referenceApi.categories()
  });
  const priorities = useQuery({
    queryKey: ["priorities"],
    queryFn: () => referenceApi.priorities()
  });
  const assignableUsers = useQuery({
    queryKey: ["assignable-users", "new-ticket"],
    queryFn: () => referenceApi.assignableUsers()
  });

  const form = useForm<CreateTicketForm>({
    defaultValues: {
      title: "",
      description: "",
      category: "REQUEST",
      priority: "MEDIUM",
      target_department_id: 0,
      assignee_id: "",
      is_department_broadcast: false
    }
  });

  const isDepartmentBroadcast = form.watch("is_department_broadcast");

  const createMutation = useMutation({
    mutationFn: (payload: CreateTicketForm) =>
      ticketApi.create({
        ...payload,
        emitter_department_id: user?.department_id ?? payload.target_department_id,
        assignee_id: payload.is_department_broadcast ? null : payload.assignee_id || null
      }),
    onSuccess: () => {
      setFormMessage(null);
      form.reset({
        title: "",
        description: "",
        category: "REQUEST",
        priority: "MEDIUM",
        target_department_id: 0,
        assignee_id: "",
        is_department_broadcast: false
      });
      queryClient.invalidateQueries({ queryKey: ["tickets-received"] });
      queryClient.invalidateQueries({ queryKey: ["tickets-sent"] });
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
    }
  });

  const createError = useMemo(() => {
    if (!createMutation.error) return null;
    if (createMutation.error instanceof AxiosError) {
      const detail = createMutation.error.response?.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
    }
    return "Erreur pendant la creation du ticket.";
  }, [createMutation.error]);

  return (
    <section className="stack">
      <h2>Nouveau ticket</h2>
      <article className="card">
        <form
          className="stack"
          onSubmit={form.handleSubmit((values) => {
            if (createMutation.isPending) {
              setFormMessage("Envoi deja en cours...");
              return;
            }
            if (departments.isLoading || categories.isLoading || priorities.isLoading) {
              setFormMessage("Chargement des donnees...");
              return;
            }
            if (departments.isError || categories.isError || priorities.isError) {
              setFormMessage("Impossible de charger les donnees de reference.");
              return;
            }
            setFormMessage(null);
            createMutation.mutate(values);
          })}
        >
          <label>
            Titre
            <input
              {...form.register("title", {
                validate: (value) =>
                  (value || "").trim().length >= 3 || "Le titre doit contenir au moins 3 caracteres."
              })}
            />
            {form.formState.errors.title?.message ? (
              <span className="field-error">{form.formState.errors.title.message}</span>
            ) : null}
          </label>
          <label>
            Description
            <textarea
              {...form.register("description", {
                validate: (value) =>
                  (value || "").trim().length >= 3 || "La description doit contenir au moins 3 caracteres."
              })}
              rows={4}
            />
            {form.formState.errors.description?.message ? (
              <span className="field-error">{form.formState.errors.description.message}</span>
            ) : null}
          </label>
          <label>
            Categorie
            <select {...form.register("category", { required: true })}>
              {(categories.data || []).map((category) => (
                <option key={category} value={category}>
                  {categoryLabel(category)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Priorite
            <select {...form.register("priority", { required: true })}>
              {(priorities.data || []).map((priority) => (
                <option key={priority} value={priority}>
                  {priorityLabel(priority)}
                </option>
              ))}
            </select>
          </label>
          {user?.department_id ? (
            <p className="muted">Departement emetteur: {user.department_name || "-"}</p>
          ) : (
            <p className="muted">
              Votre profil n&apos;a pas de departement: l&apos;emetteur sera automatiquement aligne sur le departement
              destinataire.
            </p>
          )}
          <label>
            Departement destinataire
            <select
              {...form.register("target_department_id", {
                valueAsNumber: true,
                validate: (value) => Number(value) > 0 || "Selectionnez un departement destinataire."
              })}
            >
              <option value={0}>Selectionner</option>
              {(departments.data || []).map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
            {form.formState.errors.target_department_id?.message ? (
              <span className="field-error">{form.formState.errors.target_department_id.message}</span>
            ) : null}
          </label>
          <label>
            <input type="checkbox" {...form.register("is_department_broadcast")} />
            Envoyer au departement complet
          </label>
          <label>
            Destinataire specifique
            <select {...form.register("assignee_id")} disabled={isDepartmentBroadcast}>
              <option value="">Aucun</option>
              {(assignableUsers.data || []).map((assignableUser) => (
                <option key={assignableUser.id} value={assignableUser.id}>
                  {assignableUser.full_name} ({assignableUser.email})
                </option>
              ))}
            </select>
          </label>
          {formMessage ? <p className="muted">{formMessage}</p> : null}
          {createError ? <p className="error">{createError}</p> : null}
          <button type="submit">
            {createMutation.isPending ? "Creation..." : "Envoyer le ticket"}
          </button>
        </form>
      </article>
    </section>
  );
}
