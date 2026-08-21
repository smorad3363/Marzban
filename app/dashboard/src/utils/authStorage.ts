import { queryClient } from "./react-query";

export const getAuthToken = () => {
  return localStorage.getItem("token");
};

export const setAuthToken = (token: string) => {
  localStorage.setItem("token", token);
  queryClient.clear();
};

export const removeAuthToken = () => {
  localStorage.removeItem("token");
  queryClient.clear();
};
