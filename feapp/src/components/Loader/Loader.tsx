import React from 'react'
import styled, { keyframes } from 'styled-components'

const spinAnimation = keyframes`
from {
  transform: rotate(0deg);
}
to {
  transform: rotate(360deg);
}
`

const Overlay = styled.div`
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: rgba(10, 5, 39, 0.3);
  z-index: 1020;
`

const Spinner = styled.div`
  width: 50px;
  height: 50px;
  border: 5px solid #415473;
  border-top: 5px solid #f37845;
  border-radius: 50%;
  animation: ${spinAnimation} 1s linear infinite;
  margin: 0 auto;
`

export default function Loader (): React.ReactElement {
  return (
    <Overlay className="d-flex align-items-center justify-content-center">
      <Spinner />
    </Overlay>
  )
}
