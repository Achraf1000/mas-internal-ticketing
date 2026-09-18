import { apiClient, tokenStorage } from "./client";
import type {
  AdminUser,
  DepartmentHeadOverview,
  Department,
  MeResponse,
  ReportOverview,
  Ticket,
  TicketCategory,
  TicketDetail,
  TicketPriority,
  TicketStatus,
  TokenResponse,
  UserSummary
} from "../types/api";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TicketCreatePayload {
  title: string;
  description: string;
  category: TicketCategory;
  priority: TicketPriority;
  target_department_id: number;
  emitter_department_id?: number | null;
  assignee_id?: string | null;
  is_department_broadcast?: boolean;
}

export interface TicketPatchPayload {
  title?: string;
  description?: string;
  category?: TicketCategory;
  priority?: TicketPriority;
  assignee_id?: string | null;
}

export interface StatusTransitionPayload {
  to_status: TicketStatus;
  reason?: string;
}

export interface TicketListParams {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: TicketCategory;
  emitter_department_id?: number;
  target_department_id?: number;
  assignee_id?: string;
  sla_overdue?: boolean;
  include_closed?: boolean;
}

export const authApi = {
  async login(payload: LoginPayload): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>("/auth/login", payload);
    tokenStorage.setTokens(response.data);
    return response.data;
  },
  async refresh(refreshToken?: string): Promise<TokenResponse> {
    const token = refreshToken || tokenStorage.getRefreshToken();
    if (!token) {
      throw new Error("Missing refresh token");
    }
    const response = await apiClient.post<TokenResponse>("/auth/refresh", { refresh_token: token });
    tokenStorage.setTokens(response.data);
    return response.data;
  },
  async logout(): Promise<void> {
    const refresh = tokenStorage.getRefreshToken();
    if (refresh) {
      await apiClient.post("/auth/logout", { refresh_token: refresh });
    }
    tokenStorage.clear();
  },
  async me(): Promise<MeResponse> {
    const response = await apiClient.get<MeResponse>("/auth/me");
    return response.data;
  }
};

export const referenceApi = {
  async departments(): Promise<Department[]> {
    const response = await apiClient.get<Department[]>("/departments");
    return response.data;
  },
  async categories(): Promise<TicketCategory[]> {
    const response = await apiClient.get<TicketCategory[]>("/ticket-categories");
    return response.data;
  },
  async priorities(): Promise<TicketPriority[]> {
    const response = await apiClient.get<TicketPriority[]>("/priorities");
    return response.data;
  },
  async assignableUsers(departmentId?: number): Promise<UserSummary[]> {
    const response = await apiClient.get<UserSummary[]>("/users/assignable", {
      params: departmentId ? { department_id: departmentId } : undefined
    });
    return response.data;
  }
};

export const ticketApi = {
  async list(params?: TicketListParams): Promise<Ticket[]> {
    const response = await apiClient.get<Ticket[]>("/tickets", { params });
    return response.data;
  },
  async listReceived(params?: TicketListParams): Promise<Ticket[]> {
    const response = await apiClient.get<Ticket[]>("/tickets/received", { params });
    return response.data;
  },
  async listToAssign(params?: TicketListParams): Promise<Ticket[]> {
    const response = await apiClient.get<Ticket[]>("/tickets/to-assign", { params });
    return response.data;
  },
  async listSent(params?: TicketListParams): Promise<Ticket[]> {
    const response = await apiClient.get<Ticket[]>("/tickets/sent", { params });
    return response.data;
  },
  async listArchive(params?: { year?: number; month?: number; offset?: number; limit?: number }): Promise<Ticket[]> {
    const response = await apiClient.get<Ticket[]>("/tickets/archive", { params });
    return response.data;
  },
  async get(ticketId: string): Promise<TicketDetail> {
    const response = await apiClient.get<TicketDetail>(`/tickets/${ticketId}`);
    return response.data;
  },
  async create(payload: TicketCreatePayload): Promise<Ticket> {
    const response = await apiClient.post<Ticket>("/tickets", payload);
    return response.data;
  },
  async patch(ticketId: string, payload: TicketPatchPayload): Promise<Ticket> {
    const response = await apiClient.patch<Ticket>(`/tickets/${ticketId}`, payload);
    return response.data;
  },
  async changeStatus(ticketId: string, payload: StatusTransitionPayload): Promise<Ticket> {
    const response = await apiClient.post<Ticket>(`/tickets/${ticketId}/status-transitions`, payload);
    return response.data;
  },
  async comment(ticketId: string, body: string): Promise<void> {
    await apiClient.post(`/tickets/${ticketId}/comments`, { body, is_internal: false });
  },
  async uploadAttachment(ticketId: string, file: File): Promise<void> {
    const formData = new FormData();
    formData.append("file", file);
    await apiClient.post(`/tickets/${ticketId}/attachments`, formData, {
      headers: { "Content-Type": "multipart/form-data" }
    });
  },
  async downloadAttachment(ticketId: string, attachmentId: number, filename: string): Promise<void> {
    const response = await apiClient.get<Blob>(`/tickets/${ticketId}/attachments/${attachmentId}`, {
      responseType: "blob"
    });
    const url = window.URL.createObjectURL(response.data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }
};

export const reportApi = {
  async overview(): Promise<ReportOverview> {
    const response = await apiClient.get<ReportOverview>("/reports/overview");
    return response.data;
  },
  async departmentHeadOverview(params?: {
    year?: number;
    month?: number;
    member_id?: string;
  }): Promise<DepartmentHeadOverview> {
    const response = await apiClient.get<DepartmentHeadOverview>("/reports/department-head-overview", { params });
    return response.data;
  }
};

export const adminApi = {
  async users(): Promise<AdminUser[]> {
    const response = await apiClient.get<AdminUser[]>("/users");
    return response.data;
  }
};
