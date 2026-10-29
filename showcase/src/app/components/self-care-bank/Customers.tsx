import React from "react";
import axios from "axios";

import CustomerTable from "./CustomerTable";
import CustomerModal from "./CustomerModal";

const Customers: React.FC = () => {
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState("");
  const [error, setError] = React.useState(null);

  const [isOpen, setIsOpen] = React.useState(false);
  const [activeCustomer, setActiveCustomer] = React.useState(null);

  React.useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = () => {
    setLoading(true);

    setError(null);
    setData("");

    axios
      .post(
        `${process.env.NEXT_PUBLIC_SCBANK_DATA_API}/TetherfiDbRestApi/dboperations`,
        {
          dnis: "default",
          channel: "chat",
          entity: "customer",
          method: "getAllCustomers",
          details: [
            {
              columnMap: {},
            },
          ],
        },
        {
          headers: {
            "Content-Type": "application/json", // Example of custom content type
          },
        }
      )
      .then((response) => {
        setData(
          response?.data?.responseList?.map(
            (element: any) => element?.tableDetails?.columnMap
          )
        );
      })
      .catch((error) => {
        setError(error?.message);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const closeModal = () => setIsOpen(false);

  const handleRowClick = (row: any) => {
    setIsOpen(true);
    setActiveCustomer(row?.original);
  };

  const deleteCustomer = (customerId: string) => {
    axios
      .post(
        `${process.env.NEXT_PUBLIC_SCBANK_DATA_API}/TetherfiDbRestApi/dboperations`,
        {
          dnis: "default",
          channel: "chat",
          entity: "customer",
          method: "deleteCustomer",
          details: [
            {
              columnMap: { customerId: customerId },
            },
          ],
        },
        {
          headers: {
            "Content-Type": "application/json", // Example of custom content type
          },
        }
      )
      .then(() => {
        loadCustomers();
      })
      .catch((error) => {
        alert(`Error: ${error?.message}`);
      });
  };

  return (
    <div style={{ minHeight: 300 }}>
      {loading ? (
        <div style={{ color: "green" }}>Loading...</div>
      ) : error ? (
        <div style={{ color: "orangered" }}>{error}</div>
      ) : (
        <CustomerTable data={data} handleRowClick={handleRowClick} />
      )}

      <CustomerModal
        activeCustomer={activeCustomer}
        isOpen={isOpen}
        closeModal={closeModal}
        deleteCustomer={deleteCustomer}
      />
    </div>
  );
};

export default Customers;

/**
 * curl --location 'http://13.127.144.75:9099/TetherfiDbRestApi/dboperations' \
--header 'Content-Type: application/json' \
--data '{
    "dnis": "default",
    "channel": "chat",
    "entity": "customer",
    "method": "getAllCustomers",
    "details": [
        {
            "columnMap": {
            }
        }
    ]
}'
 */

/**
 * curl --location 'http://13.127.144.75:9099/TetherfiDbRestApi/dboperations' \
--header 'Content-Type: application/json' \
--data '{
    "dnis": "default",
    "channel": "chat",
    "entity": "customer",
    "method": "deleteCustomer",
    "details": [
        {
            "columnMap": {
                "customerId": "200007"
            }
        }
    ]
}'
 */
