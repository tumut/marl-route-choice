# TQ-learning with circumstantial payments

This repository is a fork from [goramos/marl-route-choice](https://github.com/goramos/marl-route-choice) with the changes made for the development of a TQ-learning variant with circumstantial payments, which was used for our research on the effects of partial participation in tolling systems that aim to minimize congestion. Conditions were introduced so that, depending on the circumstances, tolls were paid or not, thus making payment circumstantial. A variety of scenarios can be simulated by changing parameters used by the conditions.

The following parameters were added:

* `user-proportion`, or &upsilon;: controls the probability of a driver being a user, which means he always pays tolls; non-users only pay tolls if other conditions are met.
* `is-participation-fixed`: whether drivers can choose to be users or not. Effectively introduces states into the Q-learning. Went unused in our experiments.
* `obligatory-toll-percentile`, or &rho;: controls the threshold of traffic volume which makes traffic obligatory for a given link, such that 100&rho;% of links have traffic volume above the threshold.

Currently, the parameter which controls the payment mode (relevant only for &rho; > 0) is hardcoded. It can be set [here](https://github.com/tumut/tql-circumstantial-payment/blob/89b1b36a12fe4b497f68d02d52ada63fcc8da937/agent.py#L177) to:

* `'link'`: toll is only paid for links in the &rho; threshold.
* `'route'`: toll is paid for the whole route if so much as one link of the route is in the &rho; threshold.

The `aamas20` experiment with the `ala18` algorithm (`--alg`) must be used. It wasn't tested in other settings.

Setting either &upsilon; or &rho; to 1 simulates the original TQ-learning algorithm.

The `battery` folder contains the script used to run experiment batches.

## Requirements

Ensure you're using Python 2.7 and that the requirements at `requirements.txt` have been met.

## Road Networks

The road networks used in this project are available in the `networks` directory. All networks were specified following the [Transportation Networks](https://github.com/goramos/transportation_networks) project. 

## Thanks

Special thanks to [Gabriel Ramos](https://gdoramos.net) for making the code of the original TQ-learning available and for his solicitude in answering our questions whenever asked.

## License

This project uses the following license: [MIT](https://github.com/tumut/tql-circumstantial-payment/blob/1c0b859e4ac0388302fea7db403b1c80771a6163/README.md).