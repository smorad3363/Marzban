import {FC} from "react";
import {Text} from "@chakra-ui/react";
import {relativeExpiryDate} from "utils/dateFormatter";

type UserStatusProps = {
    lastOnline: string | null;
};

const convertDateFormat = (lastOnline: string | null): number | null => {
    if (!lastOnline) {
        return null;
    }

    const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/.test(lastOnline)
        ? lastOnline
        : `${lastOnline}Z`;
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return null;
    return Math.floor(date.getTime() / 1000);
};

export const OnlineStatus: FC<UserStatusProps> = ({lastOnline}) => {
    const currentTimeInSeconds = Math.floor(Date.now() / 1000);
    const unixTime = convertDateFormat(lastOnline);

    const timeDifferenceInSeconds = unixTime ? currentTimeInSeconds - unixTime : null;
    const dateInfo = unixTime ? relativeExpiryDate(unixTime) : {status: "", time: "Not Connected Yet"};

    return (
        <Text
            display="inline-block"
            fontSize="xs"
            fontWeight="medium"
            ms="0"
            mt="1"
            color="gray.600"
            _dark={{
                color: "gray.400",
            }}
        >
            {timeDifferenceInSeconds && timeDifferenceInSeconds <= 60
                ? "Online"
                : timeDifferenceInSeconds
                    ? `${dateInfo.time} ago`
                    : dateInfo.time}
        </Text>
    );
};
