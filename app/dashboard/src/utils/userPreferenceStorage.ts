const NUM_USERS_PER_PAGE_LOCAL_STORAGE_KEY = "network-console-users-per-page";
const NUM_USERS_PER_PAGE_DEFAULT = 10;
const ALLOWED_USERS_PER_PAGE = [10, 100, 250, 500, 1000];
export const getUsersPerPageLimitSize = () => {
  const numUsersPerPage =
    localStorage.getItem(NUM_USERS_PER_PAGE_LOCAL_STORAGE_KEY) ||
    NUM_USERS_PER_PAGE_DEFAULT.toString(); // this catches `null` values
  const parsed = parseInt(numUsersPerPage);
  return ALLOWED_USERS_PER_PAGE.includes(parsed)
    ? parsed
    : NUM_USERS_PER_PAGE_DEFAULT;
};

export const setUsersPerPageLimitSize = (value: string) => {
  return localStorage.setItem(NUM_USERS_PER_PAGE_LOCAL_STORAGE_KEY, value);
};
