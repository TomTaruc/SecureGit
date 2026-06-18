import { create } from 'zustand';

let _toastId = 0;

const useUIStore = create((set, get) => ({
  toasts: [],
  sidebarCollapsed: false,
  activeModal: null,
  modalData: null,

  // Toast system
  addToast: (message, type = 'info', duration = 4000) => {
    const id = ++_toastId;
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }));
    if (duration > 0) {
      setTimeout(() => get().removeToast(id), duration);
    }
    return id;
  },
  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  toastSuccess: (msg) => get().addToast(msg, 'success'),
  toastError:   (msg) => get().addToast(msg, 'error'),
  toastInfo:    (msg) => get().addToast(msg, 'info'),

  // Sidebar
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  // Modal
  openModal:  (name, data = null) => set({ activeModal: name, modalData: data }),
  closeModal: () => set({ activeModal: null, modalData: null }),
}));

export default useUIStore;
