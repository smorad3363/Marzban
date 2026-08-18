import { createHashRouter } from "react-router-dom";
import { fetch } from "../service/http";
import { getAuthToken } from "../utils/authStorage";
import { Dashboard } from "./Dashboard";
import { Admins } from "./Admins";
import { Login } from "./Login";
import { AuditLogs } from "./AuditLogs";
import { DeviceLimits } from "./DeviceLimits";
import { Plans } from "./Plans";
const fetchAdminLoader = () => {
    return fetch("/admin", {
        headers: {
            Authorization: `Bearer ${getAuthToken()}`,
        },
    });
};
export const router = createHashRouter([
    {
        path: "/",
        element: <Dashboard />,
        errorElement: <Login />,
        loader: fetchAdminLoader,
    },
    {
        path: "/login/",
        element: <Login />,
    },
    {
        path: "/admins/",
        element: <Admins />,
        errorElement: <Login />,
        loader: fetchAdminLoader,
    },
    {
        path: "/device-limits/",
        element: <DeviceLimits />,
        errorElement: <Login />,
        loader: fetchAdminLoader,
    },
    {
        path: "/plans/",
        element: <Plans />,
        errorElement: <Login />,
        loader: fetchAdminLoader,
    },
    {
        path: "/audit-logs/",
        element: <AuditLogs />,
        errorElement: <Login />,
        loader: fetchAdminLoader,
    },
]);
